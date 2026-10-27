"""Small in-memory Kafka analogue for deterministic tests and offline demos."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Record:
    topic: str
    value: dict[str, Any]
    partition: int
    offset: int
    key: str | None = None


class InMemoryBroker:
    def __init__(self, partitions: dict[str, int] | None = None) -> None:
        self.partitions = defaultdict(lambda: 1, partitions or {})
        self.records: dict[str, list[Record]] = defaultdict(list)

    def send(self, topic: str, value: dict[str, Any], key: str | None = None) -> Record:
        count = self.partitions[topic]
        partition = (
            (sum(key.encode("utf-8")) % count) if key else (len(self.records[topic]) % count)
        )
        offset = sum(1 for item in self.records[topic] if item.partition == partition)
        record = Record(topic, deepcopy(value), partition, offset, key)
        self.records[topic].append(record)
        return record

    def read(self, topic: str) -> list[Record]:
        return deepcopy(self.records[topic])
