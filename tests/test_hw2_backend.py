from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from code.web_application.backend import app, reset_recalls


PAYLOAD = {
    "productName": "Crispy Oat Bars",
    "brandName": "Sunny Pantry",
    "submitterEmail": "safety@example.edu",
    "recallDetails": "Selected boxes may contain undeclared peanuts and should be returned.",
    "category": "Packaged Foods",
    "termsAccepted": True,
}


class BackendTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_recalls()
        self.client = TestClient(app)

    def test_home_and_health(self) -> None:
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("Grocery Recall Manager", home.text)
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_create_update_delete_and_search(self) -> None:
        created = self.client.post("/api/recalls", json=PAYLOAD)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["id"], 3)

        updated_payload = {**PAYLOAD, "productName": "Updated Spinach", "brandName": "Updated Harvest"}
        updated = self.client.put("/api/recalls/1", json=updated_payload)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["productName"], "Updated Spinach")

        search = self.client.get("/api/recalls", params={"q": "updated harvest"})
        self.assertEqual([item["id"] for item in search.json()], [1])

        deleted = self.client.delete("/api/recalls/highest")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["deleted"]["id"], 3)
        self.assertEqual([item["id"] for item in self.client.get("/api/recalls").json()], [1, 2])

    def test_validation_rejects_short_details_and_unaccepted_terms(self) -> None:
        short = self.client.post("/api/recalls", json={**PAYLOAD, "recallDetails": "too short"})
        self.assertEqual(short.status_code, 422)
        unchecked = self.client.post("/api/recalls", json={**PAYLOAD, "termsAccepted": False})
        self.assertEqual(unchecked.status_code, 422)


if __name__ == "__main__":
    unittest.main()
