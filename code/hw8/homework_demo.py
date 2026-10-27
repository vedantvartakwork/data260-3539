"""Run the required CREATE_RECALL -> GET_RECALL HTTP/Kafka journey."""

from __future__ import annotations

import json
import uuid
from code.hw8.config import settings
from code.hw8.failures import valid_recall

import httpx


def main() -> None:
    endpoint = f"http://127.0.0.1:{settings.port_base}/api/hw8/entities"
    create_correlation = str(uuid.uuid4())
    create_request = {
        "correlation_id": create_correlation,
        "operation": "CREATE_RECALL",
        "data": valid_recall(),
    }
    print("Vedant Vartak - DATA 260 Homework 8 complete Kafka flow")
    print(f"CLIENT SEND CREATE_RECALL {json.dumps(create_request, sort_keys=True)}")
    create_response = httpx.post(endpoint, json=create_request, timeout=15).json()
    print(f"CLIENT RECEIVE CREATE_RECALL {json.dumps(create_response, sort_keys=True)}")
    if create_response.get("correlation_id") != create_correlation:
        raise RuntimeError("CREATE correlation_id was not preserved")

    entity_id = create_response["entity_id"]
    get_correlation = str(uuid.uuid4())
    get_request = {
        "correlation_id": get_correlation,
        "operation": "GET_RECALL",
        "data": {"entity_id": entity_id},
    }
    print(f"CLIENT SEND GET_RECALL {json.dumps(get_request, sort_keys=True)}")
    get_response = httpx.post(endpoint, json=get_request, timeout=15).json()
    print(f"CLIENT RECEIVE GET_RECALL {json.dumps(get_response, sort_keys=True)}")
    if get_response.get("correlation_id") != get_correlation:
        raise RuntimeError("GET correlation_id was not preserved")
    print(f"RETRIEVED ENTITY {json.dumps(get_response['entity'], sort_keys=True)}")
    print("PASS CREATE_RECALL -> GET_RECALL and both correlation IDs were preserved")


if __name__ == "__main__":
    main()
