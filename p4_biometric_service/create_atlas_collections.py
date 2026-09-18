"""
Creates the PramaanX collections in MongoDB Atlas with schema validation
and indexes already applied. Run this ONCE against a fresh database.

Usage:
    export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority"
    python create_atlas_collections.py

Safe to re-run: it skips any collection that already exists rather than
erroring or wiping data.
"""
from __future__ import annotations

import os
import sys

from pymongo import ASCENDING, MongoClient
from pymongo.errors import CollectionInvalid

DB_NAME = "pramaanx"


def get_client() -> MongoClient:
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        sys.exit("MONGODB_URI is not set. Export it before running this script.")
    client = MongoClient(uri)
    # Fail fast and clearly if the URI, credentials, or IP allowlist are wrong,
    # instead of every later operation silently timing out.
    client.admin.command("ping")
    return client


DOCUMENTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["document_number", "document_type", "full_name"],
        "properties": {
            "document_number": {"bsonType": "string"},
            "document_type": {"enum": ["passport", "visa", "national_id"]},
            "full_name": {"bsonType": "string"},
            "date_of_birth": {"bsonType": ["date", "null"]},
            "nationality": {"bsonType": ["string", "null"]},
            "date_of_issue": {"bsonType": ["date", "null"]},
            "date_of_expiry": {"bsonType": ["date", "null"]},
            "issuing_authority": {"bsonType": ["string", "null"]},
            "mrz_string": {"bsonType": ["string", "null"]},
            "reference_photo_url": {"bsonType": ["string", "null"]},
        },
    }
}

VERIFICATION_RESULTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["submitted_at", "face_verification", "risk"],
        "properties": {
            "submission_id": {"bsonType": ["string", "null"]},
            "document_number": {"bsonType": ["string", "null"]},
            "officer_id": {"bsonType": ["objectId", "null"]},
            "submitted_at": {"bsonType": "date"},
            "face_verification": {
                "bsonType": "object",
                "required": ["found_in_database", "is_match", "threshold_used"],
                "properties": {
                    "found_in_database": {"bsonType": "bool"},
                    "similarity": {"bsonType": ["double", "int", "null"]},
                    "is_match": {"bsonType": "bool"},
                    "threshold_used": {"bsonType": ["double", "int"]},
                    "liveness_passed": {"bsonType": ["bool", "null"]},
                    "liveness_performed": {"bsonType": ["bool", "null"]},
                    "confidence_label": {"bsonType": ["string", "null"]},
                    "reason": {"bsonType": ["string", "null"]},
                    "error": {"bsonType": ["string", "null"]},
                },
            },
            "risk": {
                "bsonType": "object",
                "required": ["score", "level"],
                "properties": {
                    "score": {"bsonType": "int", "minimum": 0, "maximum": 100},
                    "level": {"enum": ["LOW", "MEDIUM", "HIGH"]},
                    "reasons": {"bsonType": ["array", "null"]},
                },
            },
            "manual_review": {"bsonType": ["object", "null"]},
        },
    }
}

COLLECTIONS: dict[str, dict | None] = {
    "documents": DOCUMENTS_VALIDATOR,
    "verification_results": VERIFICATION_RESULTS_VALIDATOR,
    "alerts": None,
    "users": None,
    "audit_logs": None,
    "captures": None,
}


def create_collections(db) -> None:
    existing = set(db.list_collection_names())
    for name, validator in COLLECTIONS.items():
        if name in existing:
            print(f"  {name}: already exists, skipping create")
            continue
        kwargs = {"validator": validator} if validator else {}
        try:
            db.create_collection(name, **kwargs)
            print(f"  {name}: created" + (" with validator" if validator else ""))
        except CollectionInvalid:
            print(f"  {name}: already exists (race), skipping")


def create_indexes(db) -> None:
    db.documents.create_index([("document_number", ASCENDING)], unique=True)

    db.verification_results.create_index([("document_number", ASCENDING)])
    db.verification_results.create_index([("submitted_at", ASCENDING)])
    db.verification_results.create_index([("risk.level", ASCENDING)])
    db.verification_results.create_index([("manual_review.status", ASCENDING)])

    db.alerts.create_index([("status", ASCENDING)])
    db.alerts.create_index([("created_at", ASCENDING)])

    db.users.create_index([("email", ASCENDING)], unique=True)

    db.audit_logs.create_index([("timestamp", ASCENDING)])
    db.audit_logs.create_index([("actor_id", ASCENDING)])

    # TTL index: capture rows auto-delete when expires_at passes. Live photos
    # that aren't tied to a kept verification result shouldn't linger.
    db.captures.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)

    print("  all indexes created (or already present)")


def main() -> None:
    client = get_client()
    db = client[DB_NAME]
    print(f"Connected. Creating collections in database '{DB_NAME}'...")
    create_collections(db)
    print("Creating indexes...")
    create_indexes(db)
    print("Done. Run `db.getCollectionNames()` / `db.<name>.getIndexes()` in mongosh to confirm.")


if __name__ == "__main__":
    main()
