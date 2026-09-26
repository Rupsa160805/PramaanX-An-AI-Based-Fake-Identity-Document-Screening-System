"""Local reference-store adapter used when P3's database module is absent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ReferenceStoreError(RuntimeError):
    """Raised when the configured local reference store cannot be read."""


class ReferenceDatabase:
    def __init__(self, json_path: str | Path):
        self.json_path = Path(json_path)

    def lookup_by_document_number(self, document_number: str) -> dict[str, Any] | None:
        if not self.json_path.exists():
            raise ReferenceStoreError(
                f"reference database does not exist: {self.json_path}"
            )
        try:
            payload = json.loads(self.json_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ReferenceStoreError(
                f"reference database could not be read: {self.json_path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ReferenceStoreError(
                f"reference database contains invalid JSON: {self.json_path}"
            ) from exc
        records = (
            payload.get("records", payload) if isinstance(payload, dict) else payload
        )
        if not isinstance(records, list):
            raise ReferenceStoreError(
                "reference database must contain a list of records"
            )
        wanted = document_number.strip().upper()
        for record in records:
            if not isinstance(record, dict):
                continue
            if str(record.get("document_number", "")).strip().upper() == wanted:
                return record
        return None


def lookup_by_document_number(
    document_number: str, json_path: str | Path = "demo_data/reference_records.json"
) -> dict[str, Any] | None:
    return ReferenceDatabase(json_path).lookup_by_document_number(document_number)
