"""Small, dependency-free adapter for Ollama's chat API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CompletionResult:
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    total_duration_ns: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class ModelClientError(RuntimeError):
    """Raised when Ollama cannot return a usable response."""


class OllamaClient:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.0,
        timeout: float = 180.0,
    ) -> None:
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        self.base_url = (base_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def complete(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        *,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> CompletionResult:
        """Complete a chat turn through a stable project-level interface."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.temperature if temperature is None else temperature,
                "num_ctx": 4096,
                "num_predict": 320,
            },
        }
        if os.environ.get("OLLAMA_SEED"):
            payload["options"]["seed"] = int(os.environ["OLLAMA_SEED"])
        if tools:
            payload["tools"] = tools
        if json_mode:
            payload["format"] = "json"

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelClientError(f"Ollama request failed: {exc}") from exc

        try:
            return CompletionResult(
                content=str(body["message"]["content"]),
                input_tokens=int(body.get("prompt_eval_count", 0)),
                output_tokens=int(body.get("eval_count", 0)),
                model=str(body.get("model", self.model)),
                total_duration_ns=int(body.get("total_duration", 0)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelClientError("Ollama returned an unexpected response shape") from exc


def complete(
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]] | None = None,
) -> CompletionResult:
    """Convenience interface using the default client configuration."""
    return OllamaClient().complete(messages, tools=tools)
