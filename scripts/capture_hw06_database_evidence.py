#!/usr/bin/env python3
"""Exercise HW6 MongoDB CRUD and save machine-readable validation evidence."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from pymongo.errors import WriteError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from code.hw6.db import ensure_collections
from code.web_application.backend import app


def response_record(response) -> dict:
    try:
        body = response.json()
    except Exception:
        body = None
    return {"status_code": response.status_code, "body": body}


def main() -> None:
    db = ensure_collections()
    db.recall_documents.delete_many({})
    client = TestClient(app)
    payload = {
        "title": "HW6 Frozen Berry Recall",
        "description": "Selected packages may contain an undeclared allergen.",
        "category": "Produce",
        "status": "active",
        "recalled_at": datetime.now(timezone.utc).isoformat(),
    }
    create = client.post("/api/v1/documents", json=payload)
    created = create.json()
    document_id = created["id"]
    evidence = {
        "student": "Vedant Vartak",
        "database": db.name,
        "create": response_record(create),
        "list": response_record(client.get("/api/v1/documents?limit=50")),
        "get_one": response_record(client.get(f"/api/v1/documents/{document_id}")),
        "update": response_record(client.patch(f"/api/v1/documents/{document_id}", json={"status": "monitoring"})),
        "invalid_missing_fields": response_record(client.post("/api/v1/documents", json={"title": "Only a title"})),
        "invalid_enum": response_record(client.post("/api/v1/documents", json={**payload, "category": "Invalid"})),
        "invalid_type": response_record(client.post("/api/v1/documents", json={**payload, "recalled_at": "not-a-datetime"})),
        "mongo_schema_validation": None,
        "delete": response_record(client.delete(f"/api/v1/documents/{document_id}")),
        "get_after_delete": response_record(client.get(f"/api/v1/documents/{document_id}")),
    }
    try:
        db.recall_documents.insert_one({"title": "Bypasses Pydantic but lacks required fields"})
        evidence["mongo_schema_validation"] = {"blocked": False}
    except WriteError as exc:
        evidence["mongo_schema_validation"] = {"blocked": True, "code": exc.code, "message": str(exc).split(" full error:")[0]}

    db.recall_documents.insert_many(
        [
            {
                **payload,
                "recalled_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "title": f"Seeded grocery recall {index}",
            }
            for index in range(1, 6)
        ]
    )
    evidence["compass_shell_snapshot"] = {
        "collections": sorted(db.list_collection_names()),
        "recall_document_count": db.recall_documents.count_documents({}),
        "sample_documents": [
            {**row, "_id": str(row["_id"])}
            for row in db.recall_documents.find().sort("created_at", -1).limit(3)
        ],
        "recall_validator": db.command("listCollections", filter={"name": "recall_documents"})["cursor"]["firstBatch"][0]["options"]["validator"],
    }
    destination = PROJECT_ROOT / "reports" / "hw06" / "raw" / "database_crud_evidence.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(evidence, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, default=str))


if __name__ == "__main__":
    main()
