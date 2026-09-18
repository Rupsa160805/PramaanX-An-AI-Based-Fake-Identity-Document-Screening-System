"""MongoDB Atlas repository with an explicit local fallback.

The repository owns the Mongo client lifecycle and keeps all persistence calls
behind one small interface.  This lets the Flask API run offline for tests
while using the Atlas collections and validators when ``MONGODB_URI`` is set.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .database import ReferenceDatabase, ReferenceStoreError

try:  # Optional at import time so the offline test suite stays lightweight.
    from bson import ObjectId
    from pymongo import ASCENDING, DESCENDING, MongoClient
    from pymongo.errors import PyMongoError
except ImportError:  # pragma: no cover - exercised when pymongo is absent
    ObjectId = None  # type: ignore[assignment]
    ASCENDING = DESCENDING = None  # type: ignore[assignment]
    MongoClient = None  # type: ignore[assignment,misc]

    class PyMongoError(Exception):
        pass


logger = logging.getLogger(__name__)


class DatabaseConnectionError(RuntimeError):
    """Raised when the configured Atlas repository cannot be used."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    """Convert BSON/native values into JSON response values."""
    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _normalise_document(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    result = dict(_json_safe(record))
    reference = (
        result.get("reference_photo_url")
        or result.get("photo_path")
        or result.get("reference_photo_path")
        or result.get("photo")
    )
    if reference:
        result["photo_path"] = reference
    return result


class DatabaseStore:
    """Shared document/result/alert/audit repository.

    ``P4_DATABASE_MODE=local`` always uses the JSON-backed demo adapter.
    ``P4_DATABASE_MODE=mongo`` requires a reachable Atlas URI.  ``auto`` uses
    local mode only when no URI was supplied; a supplied but unreachable URI
    is reported as degraded instead of silently writing to the wrong store.
    """

    def __init__(self, settings: Any):
        self.settings = settings
        self.client: Any | None = None
        self.mongo: Any | None = None
        self.error: str | None = None
        self.mode = "local"
        self.connected = True
        self._lock = threading.RLock()
        self._reference = ReferenceDatabase(settings.database_path)
        self._state_path = Path(
            settings.local_database_path
            or (Path(settings.capture_dir) / "pramaanx_local_database.json")
        )
        self._local_state: dict[str, list[dict[str, Any]]] = {
            "verification_results": [],
            "alerts": [],
            "audit_logs": [],
        }
        self._load_local_state()

        wants_mongo = settings.database_mode == "mongo" or (
            settings.database_mode == "auto" and settings.mongodb_uri
        )
        if wants_mongo:
            self.mode = "mongo"
            self.connected = False
            self._connect_mongo()

    def _load_local_state(self) -> None:
        try:
            if self._state_path.exists():
                payload = json.loads(self._state_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    for key in self._local_state:
                        value = payload.get(key)
                        if isinstance(value, list):
                            self._local_state[key] = value
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("local database state could not be loaded: %s", exc)

    def _save_local_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(self._local_state, indent=2), encoding="utf-8"
        )

    def _connect_mongo(self) -> None:
        if MongoClient is None:
            self.error = "pymongo is not installed"
            if self.settings.database_mode == "mongo":
                raise DatabaseConnectionError(self.error)
            return
        try:
            self.client = MongoClient(
                self.settings.mongodb_uri,
                serverSelectionTimeoutMS=self.settings.mongodb_server_selection_timeout_ms,
                connectTimeoutMS=self.settings.mongodb_server_selection_timeout_ms,
                retryWrites=True,
            )
            self.client.admin.command("ping")
            self.mongo = self.client[self.settings.mongodb_database]
            self._ensure_schema()
            self.connected = True
            self.error = None
        except Exception as exc:  # PyMongo may wrap network/TLS failures.
            self.error = str(exc)
            self.connected = False
            if self.client is not None:
                self.client.close()
            self.client = None
            self.mongo = None
            if self.settings.database_mode == "mongo":
                raise DatabaseConnectionError(
                    f"MongoDB connection failed: {self.error}"
                ) from exc
            logger.warning("MongoDB configured but unavailable: %s", self.error)

    def _ensure_schema(self) -> None:
        if self.mongo is None:
            return
        validators = {
            "documents": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["document_number"],
                    "properties": {
                        "document_number": {"bsonType": "string"},
                        "document_type": {"enum": ["passport", "visa", "national_id"]},
                        "reference_photo_url": {"bsonType": "string"},
                    },
                }
            },
            "verification_results": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["document_number", "face_verification", "risk"],
                    "properties": {
                        "document_number": {"bsonType": ["string", "null"]},
                        "face_verification": {"bsonType": "object"},
                        "risk": {"bsonType": "object"},
                    },
                }
            },
        }
        existing = set(self.mongo.list_collection_names())
        for name, validator in validators.items():
            try:
                if name not in existing:
                    self.mongo.create_collection(
                        name,
                        validator=validator,
                        validationLevel="moderate",
                    )
                else:
                    self.mongo.command(
                        "collMod",
                        name,
                        validator=validator,
                        validationLevel="moderate",
                    )
            except PyMongoError as exc:
                # A least-privilege app user may be allowed to use existing
                # collections but not run collMod.  Indexes and CRUD can
                # still work, so retain the connection and expose the warning.
                logger.warning(
                    "MongoDB schema setup for %s was not applied: %s", name, exc
                )

        indexes = {
            "documents": [("document_number", ASCENDING, {"unique": True})],
            "verification_results": [
                ("document_number", ASCENDING, {}),
                ("submitted_at", DESCENDING, {}),
                ("risk.level", ASCENDING, {}),
                ("manual_review.status", ASCENDING, {}),
                (
                    [
                        ("submitted_at", DESCENDING),
                        ("risk.level", ASCENDING),
                    ],
                    None,
                    {},
                ),
            ],
            "alerts": [("status", ASCENDING, {}), ("created_at", DESCENDING, {})],
            "users": [("email", ASCENDING, {"unique": True})],
            "audit_logs": [
                ("timestamp", DESCENDING, {}),
                ("actor_id", ASCENDING, {}),
            ],
            "captures": [("expires_at", ASCENDING, {"expireAfterSeconds": 0})],
        }
        for collection_name, definitions in indexes.items():
            collection = self.mongo[collection_name]
            for key, direction, options in definitions:
                try:
                    if isinstance(key, list):
                        collection.create_index(key, **options)
                    else:
                        collection.create_index([(key, direction)], **options)
                except PyMongoError as exc:
                    logger.warning(
                        "MongoDB index setup for %s was not applied: %s",
                        collection_name,
                        exc,
                    )

    def health(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "connected": self.connected,
            "database": self.settings.mongodb_database
            if self.mode == "mongo"
            else "local-json",
            "error": self.error,
        }

    def _require_mongo(self) -> Any:
        if self.mongo is None or not self.connected:
            raise DatabaseConnectionError(self.error or "database is unavailable")
        return self.mongo

    def lookup_document(self, document_number: str) -> dict[str, Any] | None:
        wanted = str(document_number).strip().upper()
        if self.mode == "mongo":
            record = self._require_mongo().documents.find_one(
                {"document_number": wanted}
            )
            return _normalise_document(record)
        try:
            record = self._reference.lookup_by_document_number(wanted)
        except ReferenceStoreError:
            raise
        if not record:
            return None
        result = _normalise_document(record)
        if result and result.get("photo_path"):
            path = Path(str(result["photo_path"]))
            if not path.is_absolute():
                candidates = [
                    self.settings.database_path.parent / path,
                    self.settings.database_path.parent.parent / path,
                ]
                result["photo_path"] = str(
                    next(
                        (candidate for candidate in candidates if candidate.exists()),
                        candidates[0],
                    )
                )
        return result

    def record_verification(
        self,
        result: dict[str, Any],
        *,
        officer_id: str | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        submission_id = str(result.get("request_id") or uuid.uuid4())
        document_number = result.get("document_number")
        now = _now()
        risk = result.get("risk") or {}
        level = str(risk.get("level", "medium")).lower()
        record = dict(result)
        record.update(
            {
                "submission_id": submission_id,
                "document_number": document_number,
                "officer_id": officer_id,
                "submitted_at": now,
                "created_at": now,
                "manual_review": {
                    "status": "pending" if level in {"medium", "high"} else "approved",
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "notes": None,
                },
            }
        )
        if self.mode == "mongo":
            database = self._require_mongo()
            inserted = database.verification_results.insert_one(record)
            record["_id"] = inserted.inserted_id
            if level in {"medium", "high"}:
                alert = {
                    "verification_result_id": inserted.inserted_id,
                    "document_number": document_number,
                    "risk_level": level.upper(),
                    "reason_summary": "; ".join(risk.get("reasons") or [])
                    or "Risk indicators require officer review.",
                    "status": "open",
                    "created_at": now,
                    "resolved_by": None,
                    "resolved_at": None,
                }
                database.alerts.insert_one(alert)
            database.audit_logs.insert_one(
                self._audit_record(
                    actor_id=officer_id,
                    action="submit_verification",
                    target_type="verification_result",
                    target_id=inserted.inserted_id,
                    metadata={"submission_id": submission_id, "risk_level": level},
                    ip_address=ip_address,
                )
            )
            return _json_safe(record)

        with self._lock:
            record["_id"] = submission_id
            self._local_state["verification_results"].append(_json_safe(record))
            if level in {"medium", "high"}:
                self._local_state["alerts"].append(
                    {
                        "_id": str(uuid.uuid4()),
                        "verification_result_id": submission_id,
                        "document_number": document_number,
                        "risk_level": level.upper(),
                        "reason_summary": "; ".join(risk.get("reasons") or [])
                        or "Risk indicators require officer review.",
                        "status": "open",
                        "created_at": now.isoformat(),
                        "resolved_by": None,
                        "resolved_at": None,
                    }
                )
            self._local_state["audit_logs"].append(
                self._json_audit_record(
                    actor_id=officer_id,
                    action="submit_verification",
                    target_type="verification_result",
                    target_id=submission_id,
                    metadata={"submission_id": submission_id, "risk_level": level},
                    ip_address=ip_address,
                )
            )
            self._save_local_state()
        return _json_safe(record)

    @staticmethod
    def _audit_record(
        *,
        actor_id: str | None,
        action: str,
        target_type: str,
        target_id: Any,
        metadata: dict[str, Any],
        ip_address: str | None,
    ) -> dict[str, Any]:
        return {
            "actor_id": actor_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "metadata": metadata,
            "ip_address": ip_address or "unknown",
            "timestamp": _now(),
        }

    @classmethod
    def _json_audit_record(cls, **kwargs: Any) -> dict[str, Any]:
        return _json_safe(cls._audit_record(**kwargs))

    def list_verifications(
        self, *, limit: int = 25, skip: int = 0, search: str | None = None
    ) -> dict[str, Any]:
        limit = max(1, min(int(limit), 100))
        skip = max(0, int(skip))
        if self.mode == "mongo":
            database = self._require_mongo()
            query: dict[str, Any] = {}
            if search and search.strip():
                query["document_number"] = {
                    "$regex": search.strip(),
                    "$options": "i",
                }
            cursor = (
                database.verification_results.find(query)
                .sort("submitted_at", DESCENDING)
                .skip(skip)
                .limit(limit)
            )
            return {
                "items": [_json_safe(item) for item in cursor],
                "total": database.verification_results.count_documents(query),
            }
        records = list(reversed(self._local_state["verification_results"]))
        if search and search.strip():
            needle = search.strip().upper()
            records = [
                item
                for item in records
                if needle in str(item.get("document_number") or "").upper()
            ]
        return {
            "items": records[skip : skip + limit],
            "total": len(records),
        }

    def dashboard(self) -> dict[str, Any]:
        if self.mode == "mongo":
            database = self._require_mongo()
            day_start = datetime.combine(
                _now().date(), datetime.min.time(), tzinfo=timezone.utc
            )
            total = database.verification_results.count_documents({})
            today = database.verification_results.count_documents(
                {"submitted_at": {"$gte": day_start}}
            )
            high = database.verification_results.count_documents({"risk.level": "high"})
            flagged = database.verification_results.count_documents(
                {"risk.level": {"$in": ["medium", "high"]}}
            )
            open_alerts = database.alerts.count_documents({"status": "open"})
            recent = list(
                database.verification_results.find({})
                .sort("submitted_at", DESCENDING)
                .limit(5)
            )
            return {
                "total_screenings": total,
                "today_checks": today,
                "verified": max(0, total - flagged),
                "flagged": flagged,
                "high_risk": high,
                "open_alerts": open_alerts,
                "recent": [_json_safe(item) for item in recent],
            }
        records = self._local_state["verification_results"]
        return {
            "total_screenings": len(records),
            "today_checks": sum(
                str(item.get("submitted_at", ""))[:10] == _now().date().isoformat()
                for item in records
            ),
            "verified": sum(
                str((item.get("risk") or {}).get("level", "")).lower() == "low"
                for item in records
            ),
            "flagged": sum(
                str((item.get("risk") or {}).get("level", "")).lower()
                in {"medium", "high"}
                for item in records
            ),
            "high_risk": sum(
                str((item.get("risk") or {}).get("level", "")).lower() == "high"
                for item in records
            ),
            "open_alerts": sum(
                item.get("status") == "open" for item in self._local_state["alerts"]
            ),
            "recent": list(reversed(records[-5:])),
        }

    def list_alerts(self, *, status: str | None = "open") -> list[dict[str, Any]]:
        if self.mode == "mongo":
            query = {"status": status} if status else {}
            return [
                _json_safe(item)
                for item in self._require_mongo()
                .alerts.find(query)
                .sort("created_at", DESCENDING)
            ]
        records = list(reversed(self._local_state["alerts"]))
        return [item for item in records if not status or item.get("status") == status]

    def authenticate_user(self, email: str, password: str) -> dict[str, Any] | None:
        """Authenticate an active Atlas user without ever returning its hash."""
        if self.mode != "mongo":
            return None
        user = self._require_mongo().users.find_one(
            {"email": email.strip().lower(), "active": True}
        )
        if not user:
            return None
        password_hash = str(user.get("password_hash", ""))
        valid = False
        try:
            import bcrypt

            try:
                valid = bcrypt.checkpw(
                    password.encode("utf-8"), password_hash.encode("utf-8")
                )
            except (TypeError, ValueError):
                # Atlas may contain hashes created by Werkzeug instead of
                # bcrypt.  Fall through to the compatible verifier below;
                # malformed hashes must never become a 500 response.
                valid = False
        except ImportError:
            pass
        if not valid:
            try:
                from werkzeug.security import check_password_hash

                valid = check_password_hash(password_hash, password)
            except (ImportError, ValueError, TypeError):
                valid = False
        if not valid:
            return None
        now = _now()
        self._require_mongo().users.update_one(
            {"_id": user["_id"]}, {"$set": {"last_login_at": now}}
        )
        self._require_mongo().audit_logs.insert_one(
            self._audit_record(
                actor_id=user["_id"],
                action="login",
                target_type="document",
                target_id=user["_id"],
                metadata={},
                ip_address=None,
            )
        )
        return {
            "user_id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role", "officer"),
        }

    def resolve_alert(self, alert_id: str, *, actor_id: str | None = None) -> bool:
        now = _now()
        if self.mode == "mongo":
            if ObjectId is None:
                return False
            try:
                object_id = ObjectId(alert_id)
            except Exception:
                return False
            database = self._require_mongo()
            alert = database.alerts.find_one({"_id": object_id})
            if not alert:
                return False
            database.alerts.update_one(
                {"_id": object_id},
                {
                    "$set": {
                        "status": "resolved",
                        "resolved_by": actor_id,
                        "resolved_at": now,
                    }
                },
            )
            database.audit_logs.insert_one(
                self._audit_record(
                    actor_id=actor_id,
                    action="alert_resolved",
                    target_type="alert",
                    target_id=object_id,
                    metadata={},
                    ip_address=None,
                )
            )
            return True
        for alert in self._local_state["alerts"]:
            if alert.get("_id") == alert_id:
                alert.update(
                    {
                        "status": "resolved",
                        "resolved_by": actor_id,
                        "resolved_at": now.isoformat(),
                    }
                )
                self._save_local_state()
                return True
        return False

    def register_capture(
        self,
        file_path: str,
        *,
        used_in_verification_id: str | None = None,
        retention_hours: int = 24,
    ) -> None:
        if self.mode != "mongo":
            return
        database = self._require_mongo()
        database.captures.insert_one(
            {
                "file_path": file_path,
                "captured_at": _now(),
                "used_in_verification_id": used_in_verification_id,
                "expires_at": _now() + timedelta(hours=retention_hours),
            }
        )

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
