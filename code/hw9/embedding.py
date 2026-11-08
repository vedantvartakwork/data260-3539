"""Small deterministic semantic embedding used for reproducible cache experiments."""

from __future__ import annotations

import hashlib
import math
import re

TOKEN_RE = re.compile(r"[a-z0-9]+")
CODE_RE = re.compile(r"rec-3539-\d{5}", re.IGNORECASE)
SYNONYMS = {
    "amount": "units",
    "many": "units",
    "quantity": "units",
    "unit": "units",
    "affected": "units",
    "impacted": "units",
    "maker": "manufacturer",
    "company": "manufacturer",
    "brand": "manufacturer",
    "manufactured": "manufacturer",
    "made": "manufacturer",
    "item": "product",
    "food": "product",
    "notice": "recall",
    "warning": "recall",
    "reason": "details",
    "problem": "details",
    "issue": "details",
    "instructions": "guidance",
    "action": "guidance",
    "do": "guidance",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "by",
    "for",
    "from",
    "in",
    "is",
    "me",
    "of",
    "on",
    "please",
    "tell",
    "the",
    "to",
    "was",
    "what",
    "which",
    "who",
}


class DomainEmbeddingModel:
    """Hashing embedding with domain synonym normalization and cosine-ready output."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    @staticmethod
    def normalize(text: str) -> list[str]:
        tokens = []
        for token in TOKEN_RE.findall(text.lower()):
            if token in STOPWORDS:
                continue
            tokens.append(SYNONYMS.get(token, token))
        return tokens

    def _bucket(self, feature: str) -> tuple[int, float]:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        number = int.from_bytes(digest, "little")
        return number % self.dimensions, 1.0 if number & 1 else -1.0

    def embed(self, text: str) -> list[float]:
        tokens = self.normalize(text)
        vector = [0.0] * self.dimensions
        features = [(token, 1.0) for token in tokens]
        features.extend((f"{a}_{b}", 0.65) for a, b in zip(tokens, tokens[1:], strict=False))
        code = CODE_RE.search(text)
        if code:
            features.append((f"entity:{code.group(0).lower()}", 1.8))
        token_set = set(tokens)
        intent = "summary"
        for candidate in ("units", "manufacturer", "product", "details", "guidance"):
            if candidate in token_set:
                intent = candidate
                break
        if code:
            features.append((f"intent:{intent}", 4.0))
        for feature, weight in features:
            index, sign = self._bucket(feature)
            vector[index] += sign * weight
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude:
            vector = [value / magnitude for value in vector]
        return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))
