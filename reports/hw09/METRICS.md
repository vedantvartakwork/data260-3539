# Homework 9 Metrics

## Redis ingress workload

- Queries: 12
- Cache hits / misses: 6 / 6
- Hit rate: 50.0%
- Mean cached latency: 0.722 ms
- Mean non-cached local-model latency: 9377.214 ms

## Frozen 40-case threshold sweep

| Threshold | Hit rate | False-hit rate | Mean latency (ms) | Total cost |
|---:|---:|---:|---:|---:|
| 0.75 | 75.00% | 50.00% | 0.339 | $2.520 |
| 0.80 | 75.00% | 50.00% | 0.203 | $2.520 |
| 0.85 | 75.00% | 50.00% | 0.199 | $2.520 |
| 0.90 | 75.00% | 50.00% | 0.194 | $2.520 |
| 0.95 | 47.50% | 0.00% | 0.195 | $0.042 |

Cost model: $0.002 per cache miss and $0.25 support cost per false hit.
Chosen threshold: **0.95**. 0.95 removes observed false hits at far lower expected cost than 0.85, while retaining exact and high-confidence paraphrase reuse.

## Self-improving variants (held-out test set)

| Variant | Correct | Incorrect | Avg attempts | Avg latency (ms) |
|---|---:|---:|---:|---:|
| Baseline | 6 | 2 | 1.000 | 0.002 |
| Evaluator Repair | 8 | 0 | 1.250 | 0.003 |
| Lesson Memory | 8 | 0 | 1.000 | 0.050 |
| Validated Improvement | 8 | 0 | 1.000 | 0.046 |
