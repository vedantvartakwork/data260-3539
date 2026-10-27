"""Pure grocery-recall domain service used by the Kafka worker and tests."""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from typing import Any

VALID_CATEGORIES = {
    "Produce",
    "Meat and Seafood",
    "Dairy and Refrigerated",
    "Packaged Foods",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RecallService:
    """Create and retrieve recall notices with correlation-id idempotency."""

    def __init__(self) -> None:
        self.entities: dict[str, dict[str, Any]] = {}
        self.responses_by_correlation: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _error(correlation_id: str, message: str) -> dict[str, Any]:
        return {"correlation_id": correlation_id, "success": False, "error": message}

    @staticmethod
    def validate_create(data: Any) -> str | None:
        if not isinstance(data, dict):
            return "data must be an object"
        required_strings = (
            "product_name",
            "recall_code",
            "brand_name",
            "submitter_email",
            "category",
            "recall_details",
        )
        for field in required_strings:
            if not isinstance(data.get(field), str) or not data[field].strip():
                return f"{field} is required"
        if not EMAIL_RE.fullmatch(data["submitter_email"].strip()):
            return "submitter_email must be a valid email address"
        if data["category"] not in VALID_CATEGORIES:
            return "category is invalid"
        units = data.get("units_affected")
        if isinstance(units, bool) or not isinstance(units, int) or units <= 0:
            return "units_affected must be a positive integer"
        if data.get("terms_accepted") is not True:
            return "terms_accepted must be true"
        return None

    def process(self, message: Any) -> dict[str, Any]:
        if not isinstance(message, dict):
            return self._error("", "Request must be a JSON object")
        correlation_id = message.get("correlation_id")
        if not isinstance(correlation_id, str) or not correlation_id:
            return self._error("", "correlation_id is required")
        if correlation_id in self.responses_by_correlation:
            replay = deepcopy(self.responses_by_correlation[correlation_id])
            replay["duplicate"] = True
            return replay
        if not isinstance(message.get("reply_to"), str) or not message["reply_to"]:
            return self._error(correlation_id, "reply_to is required")

        operation = message.get("operation")
        data = message.get("data")
        if operation == "CREATE_RECALL":
            error = self.validate_create(data)
            if error:
                response = self._error(correlation_id, error)
            else:
                entity_id = str(uuid.uuid4())
                entity = {"entity_id": entity_id, **deepcopy(data)}
                self.entities[entity_id] = entity
                response = {
                    "correlation_id": correlation_id,
                    "success": True,
                    "entity_id": entity_id,
                    "message": "Recall created",
                }
        elif operation == "GET_RECALL":
            entity_id = data.get("entity_id") if isinstance(data, dict) else None
            if not entity_id:
                response = self._error(correlation_id, "entity_id is required")
            elif entity_id not in self.entities:
                response = self._error(correlation_id, "Entity not found")
            else:
                response = {
                    "correlation_id": correlation_id,
                    "success": True,
                    "entity": deepcopy(self.entities[entity_id]),
                }
        else:
            response = self._error(correlation_id, "Unknown operation")

        self.responses_by_correlation[correlation_id] = deepcopy(response)
        return response
