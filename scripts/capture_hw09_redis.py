"""Capture the live Redis 8 vector-set state used by the HW9 report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from code.hw9.agent_adapter import GroceryRecallAgent
from code.hw9.config import settings
from code.hw9.query_service import SemanticQueryService
from code.hw9.semantic_cache import RedisSemanticCache
from code.hw9.store import RecallStore

import redis


def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return [decode(item) for item in value]
    if isinstance(value, dict):
        return {decode(key): decode(item) for key, item in value.items()}
    return value


def main() -> None:
    client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=False)
    cache = RedisSemanticCache(client)
    cache.clear()
    store = RecallStore(ROOT / "reports" / "hw09" / "raw" / "hw09.db", client)
    service = SemanticQueryService(cache, GroceryRecallAgent(store, use_ollama=False))
    miss = service.query("How many units are affected by REC-3539-00001?", threshold=0.95)
    hit = service.query("What quantity is impacted in recall REC-3539-00001?", threshold=0.95)
    info = client.info("server")
    payload = {
        "student": "Vedant Vartak",
        "redis_version": decode(info.get("redis_version")),
        "redis_mode": decode(info.get("redis_mode")),
        "vector_command": "VADD / VSIM (native cosine vector set)",
        "vector_index_key": settings.semantic_index,
        "vector_count": int(client.execute_command("VCARD", settings.semantic_index)),
        "all_prefix_keys": sorted(decode(key) for key in client.scan_iter(match="s3539:*")),
        "view_count": int(client.get(f"{settings.view_prefix}REC-3539-00001") or 0),
        "cache_miss": miss,
        "cache_hit": hit,
    }
    path = ROOT / "reports" / "hw09" / "raw" / "redis_state.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("Vedant Vartak - DATA 260 Homework 9 Redis evidence")
    print(json.dumps(payload, indent=2))
    print("saved=", path)
    store.close()
    client.close()


if __name__ == "__main__":
    main()
