"""Seed synthetic PramaanX reference data and a demo officer in Atlas.

Run with P4_DATABASE_MODE=mongo and MONGODB_URI configured.  The operation is
idempotent: re-running it updates the same demo records instead of duplicating
them.  No real identity or biometric data is used.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.config import Settings
from server.services.mongo_store import DatabaseStore


def _date(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def seed() -> dict[str, int | str]:
    settings = Settings.from_env()
    settings.validate()
    if settings.database_mode != "mongo":
        raise RuntimeError("Set P4_DATABASE_MODE=mongo before seeding Atlas")

    store = DatabaseStore(settings)
    database = store.mongo
    if database is None or not store.connected:
        raise RuntimeError(store.error or "Atlas is not connected")

    now = datetime.now(timezone.utc)
    records = [
        {
            "document_number": "Q2714253",
            "document_type": "passport",
            "full_name": "Synthetic Demo Person A",
            "date_of_birth": _date(1994, 5, 17),
            "nationality": "IND",
            "date_of_issue": _date(2021, 5, 17),
            "date_of_expiry": _date(2031, 5, 16),
            "issuing_authority": "Synthetic PramaanX Demo Authority",
            "mrz_string": "P<INDSYNTHETIC<<DEMO_PERSON_A<<<<<<<<<<<<<<<<",
            "reference_photo_url": "demo_artifacts/synthetic_reference_no_face.png",
        },
        {
            "document_number": "P8841207",
            "document_type": "national_id",
            "full_name": "Synthetic Demo Person B",
            "date_of_birth": _date(1988, 11, 2),
            "nationality": "IND",
            "date_of_issue": _date(2022, 11, 2),
            "date_of_expiry": _date(2032, 11, 1),
            "issuing_authority": "Synthetic PramaanX Demo Authority",
            "mrz_string": "I<INDSYNTHETIC<<DEMO_PERSON_B<<<<<<<<<<<<<<<<",
            "reference_photo_url": "demo_artifacts/synthetic_reference_no_face.png",
        },
        {
            "document_number": "DEMO-PAS-001",
            "document_type": "passport",
            "full_name": "Synthetic Demo Person A",
            "date_of_birth": _date(1994, 5, 17),
            "nationality": "IND",
            "date_of_issue": _date(2021, 5, 17),
            "date_of_expiry": _date(2031, 5, 16),
            "issuing_authority": "PramaanX Synthetic Test Authority",
            "mrz_string": "P<INDSYNTHETIC<<DEMO_PERSON_A<<<<<<<<<<<<<<<<",
            "reference_photo_url": "demo_artifacts/synthetic_reference_no_face.png",
        },
        {
            "document_number": "DEMO-AAD-001",
            "document_type": "national_id",
            "full_name": "Synthetic Demo Person C",
            "date_of_birth": _date(1994, 5, 17),
            "nationality": "IND",
            "date_of_issue": _date(2022, 5, 17),
            "date_of_expiry": _date(2032, 5, 16),
            "issuing_authority": "PramaanX Synthetic Test Authority",
            "mrz_string": "",
            "reference_photo_url": "demo_artifacts/synthetic_reference_no_face.png",
        },
    ]
    for record in records:
        record["updated_at"] = now
        database.documents.update_one(
            {"document_number": record["document_number"]},
            {"$set": record, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )

    demo_email = "demo.officer@pramaanx.local"
    database.users.update_one(
        {"email": demo_email},
        {
            "$set": {
                "name": "Synthetic Demo Officer",
                "role": "officer",
                "active": True,
                "password_hash": generate_password_hash("Demo@12345"),
                "updated_at": now,
            },
            "$setOnInsert": {"email": demo_email, "created_at": now},
        },
        upsert=True,
    )
    store.close()
    return {
        "database": settings.mongodb_database,
        "documents": len(records),
        "users": 1,
        "demo_login": f"{demo_email} / Demo@12345",
    }


if __name__ == "__main__":
    print(seed())
