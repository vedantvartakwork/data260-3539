#!/usr/bin/env python3
"""Capture live JWT and RBAC evidence against the cumulative MySQL API."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "reports/hw07/raw/jwt_rbac_http_evidence.json"
BASE = "http://127.0.0.1:8839"


def item(response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return {
        "method": response.request.method,
        "url": str(response.request.url),
        "status_code": response.status_code,
        "body": body,
    }


def main() -> None:
    client = httpx.Client(timeout=10)
    evidence: dict = {"student": "Vedant Vartak", "captured_at": datetime.now(UTC).isoformat()}
    evidence["invalid_login"] = item(
        client.post(f"{BASE}/auth/login", json={"username": "reader3539", "password": "wrong"})
    )
    tokens = {}
    for role, username, password in (
        ("reader", "reader3539", "reader-pass-3539"),
        ("writer", "writer3539", "writer-pass-3539"),
        ("moderator", "moderator3539", "moderator-pass-3539"),
    ):
        response = client.post(
            f"{BASE}/auth/login", json={"username": username, "password": password}
        )
        evidence[f"{role}_login"] = item(response)
        tokens[role] = response.json()["access_token"]
    evidence["me_missing"] = item(client.get(f"{BASE}/auth/me"))
    evidence["me_invalid"] = item(
        client.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
    )
    evidence["me_reader"] = item(
        client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {tokens['reader']}"})
    )
    evidence["list_reader"] = item(
        client.get(
            f"{BASE}/api/v1/recalls?page_size=2",
            headers={"Authorization": f"Bearer {tokens['reader']}"},
        )
    )
    payload = {
        "product_name": "HW7 JWT Evidence Granola Bars",
        "recall_code": "REC-3539-HW7JWT",
        "units_affected": 3539,
        "manufacturer_id": 15,
        "brand_name": "JWT Evidence Brand",
        "submitter_email": "hw7@example.edu",
        "category": "Packaged Foods",
        "recall_details": "Selected packages are included in the HW7 role authorization evidence run.",
        "terms_accepted": True,
    }
    evidence["create_reader"] = item(
        client.post(
            f"{BASE}/api/v1/recalls",
            json=payload,
            headers={"Authorization": f"Bearer {tokens['reader']}"},
        )
    )
    writer_create = client.post(
        f"{BASE}/api/v1/recalls",
        json=payload,
        headers={"Authorization": f"Bearer {tokens['writer']}"},
    )
    if writer_create.status_code == 409:
        # Reuse the existing evidence record on repeated captures.
        matches = client.get(
            f"{BASE}/api/v1/recalls?q=HW7%20JWT&page_size=1",
            headers={"Authorization": f"Bearer {tokens['reader']}"},
        ).json()["records"]
        recall_id = matches[0]["id"]
    else:
        recall_id = writer_create.json()["id"]
    evidence["create_writer"] = item(writer_create)
    evidence["delete_writer"] = item(
        client.delete(
            f"{BASE}/api/v1/recalls/{recall_id}",
            headers={"Authorization": f"Bearer {tokens['writer']}"},
        )
    )
    evidence["delete_moderator"] = item(
        client.delete(
            f"{BASE}/api/v1/recalls/{recall_id}",
            headers={"Authorization": f"Bearer {tokens['moderator']}"},
        )
    )
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
