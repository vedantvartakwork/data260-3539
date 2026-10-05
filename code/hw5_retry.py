"""Bounded exponential-backoff retry support for Homework 5 tools."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    timeout_seconds: float = 0.25
    base_delay_seconds: float = 0.005
    max_delay_seconds: float = 0.02


@dataclass(frozen=True)
class RetryResult:
    ok: bool
    data: Any
    error: str | None
    attempts: int
    latency_ms: float


def call_with_retry(
    operation: Callable[[], Any],
    policy: RetryPolicy = RetryPolicy(),
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.perf_counter,
) -> RetryResult:
    """Retry transient operations without exceeding attempts or timeout."""
    started = clock()
    last_error: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        remaining = policy.timeout_seconds - (clock() - started)
        if remaining <= 0:
            last_error = TimeoutError(
                f"operation timed out after {policy.timeout_seconds:.3f} seconds"
            )
            break
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(operation)
        try:
            data = future.result(timeout=remaining)
            executor.shutdown(wait=False, cancel_futures=True)
            return RetryResult(
                ok=True,
                data=data,
                error=None,
                attempts=attempt,
                latency_ms=(clock() - started) * 1000,
            )
        except FutureTimeoutError:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            last_error = TimeoutError(
                f"operation timed out after {policy.timeout_seconds:.3f} seconds"
            )
            break
        except Exception as exc:  # boundary converts exhausted failures to data
            executor.shutdown(wait=False, cancel_futures=True)
            last_error = exc
            elapsed = clock() - started
            if attempt >= policy.max_attempts or elapsed >= policy.timeout_seconds:
                break
            delay = min(
                policy.base_delay_seconds * (2 ** (attempt - 1)),
                policy.max_delay_seconds,
            )
            remaining = policy.timeout_seconds - elapsed
            if remaining <= 0:
                break
            sleep(min(delay, remaining))
    return RetryResult(
        ok=False,
        data=None,
        error=f"operation failed after {attempt} attempts: {last_error}",
        attempts=attempt,
        latency_ms=(clock() - started) * 1000,
    )
