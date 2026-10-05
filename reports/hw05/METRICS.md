# Homework 5 Metrics

Personal configuration: SID4 `3539`; PORT_BASE `8839`; PREFIX `s3539`; SEED `3539`; VERIFY_SEED `263539`; DOMAIN_ID `3` (Grocery Supply and Recall Notices).

## Retry and fault-injection results

Policy: at most 3 attempts, 100 ms total timeout, bounded exponential delays of 1 ms then 2 ms (maximum 4 ms). Each row contains 50 calls generated from VERIFY_SEED `263539`.

| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |
|---:|---:|---:|---:|
| 0% | 100% | 0.031 | 0.071 |
| 20% | 98% | 0.323 | 3.982 |
| 50% | 92% | 0.984 | 4.026 |

p99 uses the nearest-rank convention, ceil(0.99 × n); with 50 samples it is the largest observed latency. These values are recomputed from the retained final-run CSV, not mixed with a new run.

The policy is suitable for an interactive assistant because normal calls have negligible delay and transient failures usually recover within a few milliseconds. Under sustained 50% injected failure, 92% of calls still complete, but the remaining clean failures show why attempts must remain bounded. For batch processing, I would increase the total timeout and maximum attempts, add randomized jitter, and permit longer capped delays because throughput and eventual completion matter more than immediate response time.

Representative raw records demonstrate all three required paths: 0% call 1 succeeded on its first attempt; 20% call 13 recorded `failure|success`; and 20% call 46 recorded `failure|failure|failure` before returning the clean error `operation failed after 3 attempts: injected transient storage failure`.

## Local Ollama agent scenarios

| Scenario | Step count | Stop reason | Tool-call count |
|---|---:|---|---:|
| Search recall records | 2 | normal_completion | 1 |
| Retrieve one recall detail | 2 | normal_completion | 1 |
| Aggregate by category | 2 | normal_completion | 1 |
| Safety-rule block | 1 | safety_rule_block | 1 |

All four runs used local Ollama model `qwen3:8b`, temperature 0, model seed 3539, and a six-step ceiling. The first three completed after one grounded tool call and one final-answer step. The fourth stopped immediately after `execute_tool` rejected a requested search limit of 25.
