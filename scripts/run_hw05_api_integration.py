#!/usr/bin/env python3
"""Exercise the complete live HW5 HTTP CRUD flow and save evidence."""

from __future__ import annotations

import json
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/hw05/raw/api_integration.json"
BASE = "http://127.0.0.1:8839/api/v1"


def record(results: list[dict], name: str, response: httpx.Response, expected: int) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = None
    item = {"name": name, "status": response.status_code, "expected": expected, "body": body}
    results.append(item)
    if response.status_code != expected:
        raise RuntimeError(f"{name}: expected {expected}, got {response.status_code}: {response.text}")
    return body or {}


def main() -> None:
    results: list[dict] = []
    with httpx.Client(base_url=BASE, timeout=10.0) as client:
        login = client.post("/auth/login", json={"email": "admin@example.edu", "password": "password"})
        record(results, "login", login, 200)

        manufacturer = record(results, "create_manufacturer", client.post("/manufacturers", json={
            "name": "Integration Foods 3539", "contact_name": "Vedant Vartak",
            "contact_email": "integration3539@example.edu",
        }), 201)
        manufacturer_id = manufacturer["id"]
        record(results, "read_manufacturer", client.get(f"/manufacturers/{manufacturer_id}"), 200)
        record(results, "list_manufacturers", client.get("/manufacturers", params={"limit": 50}), 200)
        record(results, "update_manufacturer", client.put(f"/manufacturers/{manufacturer_id}", json={
            "name": "Integration Foods 3539 Updated", "contact_name": "Vedant Vartak",
            "contact_email": "integration3539@example.edu",
        }), 200)

        recall_payload = {
            "product_name": "Integration Recall Evidence",
            "recall_code": "REC-3539-INT01",
            "units_affected": 3539,
            "manufacturer_id": manufacturer_id,
            "brand_name": "Integration Foods 3539 Updated",
            "submitter_email": "student@example.edu",
            "category": "Packaged Foods",
            "recall_details": "Selected packages may contain an undeclared allergen and should be returned for a refund.",
            "terms_accepted": True,
        }
        recall = record(results, "create_recall", client.post("/recalls", json=recall_payload), 201)
        recall_id = recall["id"]
        listed = record(results, "list_recalls", client.get(
            "/recalls", params={"q": "Integration Recall", "page": 1, "page_size": 50}
        ), 200)
        if not any(row["id"] == recall_id for row in listed["records"]):
            raise RuntimeError("list endpoint did not return the created recall")
        record(results, "read_recall", client.get(f"/recalls/{recall_id}"), 200)
        related = record(results, "relationship_endpoint", client.get(f"/recalls/by-manufacturer/{manufacturer_id}"), 200)
        if not any(row["id"] == recall_id for row in related):
            raise RuntimeError("relationship endpoint did not return the created recall")
        record(results, "delete_referenced_manufacturer_blocked", client.delete(f"/manufacturers/{manufacturer_id}"), 409)
        recall_payload.update({"product_name": "Integration Recall Evidence Updated", "units_affected": 4000})
        record(results, "update_recall", client.put(f"/recalls/{recall_id}", json=recall_payload), 200)
        record(results, "delete_recall", client.delete(f"/recalls/{recall_id}"), 204)
        record(results, "deleted_recall_is_404", client.get(f"/recalls/{recall_id}"), 404)
        record(results, "delete_manufacturer", client.delete(f"/manufacturers/{manufacturer_id}"), 204)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"passed": len(results), "total": len(results), "checks": results}, indent=2) + "\n", encoding="utf-8")
    print(f"PASS {len(results)}/{len(results)} live API checks")
    print(OUTPUT)


if __name__ == "__main__":
    main()
