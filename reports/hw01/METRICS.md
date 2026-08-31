# Homework 1 Metrics

Generated from `reports/hw01/raw/nondeterminism_results.json`.

## Non-determinism

Tag comparison is case-insensitive, ignores leading/trailing and repeated whitespace, and treats tag order as irrelevant.

| Metric | Temp 0.7 | Temp 0.0 |
| --- | ---: | ---: |
| Successful runs | 20 | 20 |
| Distinct tag sets | 3 | 1 |
| Tags in all successful runs | `almond allergy`, `food recall` | `almond allergy`, `food recall`, `spinach contamination` |
| Tags appearing once | None | None |

| Latency metric | Temp 0.7 | Temp 0.0 |
| --- | ---: | ---: |
| p50 | 9879.65 ms | 11041.02 ms |
| p95 | 10180.85 ms | 11199.12 ms |
| p99 | 10442.98 ms | 11285.88 ms |

Percentiles use the nearest-rank method: sort successful latency values and select rank `ceil(p * n)`.
Failed runs are retained in the raw file but excluded from tag and latency calculations.
