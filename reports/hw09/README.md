# DATA 260 Homework 9 — Caching and Self-Improving Agents

Student: Vedant Vartak
SID4: 3539
Domain: Grocery Recall Manager (`DOMAIN_ID=3`)
Model: `qwen3:8b`

## Reproduce

```bash
make hw9-up
make test-hw9
make experiment-hw9
make verify-hw09
```

The Redis Stack service is isolated on port `6399`. The optional FastAPI ingress runs on port
`8840`. Redis keys and the RediSearch index are scoped by the required `s3539` prefix.

## Evidence map

- `raw/hw09_results.json`: counter accesses, ingress workload, all 200 sweep outcomes, the false
  hit, stale-answer experiment, revision sequence, lesson reuse, validation, and four variants.
- `data/cache_cases.yaml`: the frozen 40-case dataset labeled before the sweep.
- `data/{training,validation,test}_data.json`: input-only self-improvement splits.
- `data/reference_dataset.json`: evaluator-only ground truth.
- `data/lessons.json`: structured validated lesson memory.
- `verification.json`: lint, tests, required checks, hashes, commit, and tag binding.

The deterministic domain embedding keeps threshold comparisons reproducible. The normal ingress
path supports the local Ollama adapter; a grounded fallback preserves exact codes and numbers if
the model server is unavailable.
