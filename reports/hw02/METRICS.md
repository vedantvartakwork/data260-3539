# Homework 2 Metrics

Model: `qwen3:8b`; temperature: `0.7`; frozen input: `reports/hw02/cases/schema_input.json`.

## Schema-validation experiment (30 runs)

| Outcome | Count | Mean latency (ms) |
| --- | ---: | ---: |
| Valid first attempt | 30 | 3981.50 |
| Valid after 1 retry | 0 | 0.00 |
| Valid after 2+ retries | 0 | 0.00 |
| Hit turn ceiling | 0 | 0.00 |

## Turn-ceiling comparison (20 runs each)

| Turn ceiling | Completed | Completion rate | Mean latency (ms) |
| ---: | ---: | ---: | ---: |
| 2 | 20/20 | 100.0% | 3702.49 |
| 10 | 20/20 | 100.0% | 3866.74 |

**Deployment choice:** turn ceiling `2`. It produced the best completion-rate/latency result in these measured runs.

## Adversarial input (5 runs)

- Before the fix, runs reaching the ceiling: **5/5 (100.0%)**
- After the fix, runs reaching the ceiling: **0/5 (0.0%)**
- Post-fix completion rate: **5/5 (100.0%)**
- Post-fix mean latency: **4177.80 ms**
- Observed issue: the reviewer invented requirements (such as mandatory brand/lot tags) and repeatedly rejected schema-valid, factual output.
- Implemented fix: delimit untrusted recall text, explicitly ignore embedded commands, and narrow the reviewer rubric to factual support without invented tag requirements; Pydantic validation and bounded retries remain enforced.
