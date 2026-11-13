# Homework 10 — Evaluation and Observability

This submission extends the SID 3539 Homework 8 Planner/Writer/Reviewer pipeline and Homework 9 semantic cache with:

- a three-page Streamlit operations dashboard;
- a bounded DeepEval GEval evaluator backed by local `qwen3:8b`;
- a frozen 20-case human-labeled validation set and three repeat judge runs;
- correlation-preserving JSON spans for cache lookup, Kafka-style stages, evaluation, queue wait, and failure;
- a 50-confirmed-cache-miss latency experiment with p50/p95 stage metrics.

## Reproduce

```bash
.venv/bin/pip install -r requirements-hw10.txt
.venv/bin/python scripts/run_hw10_experiments.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q tests/test_hw10.py
.venv/bin/python scripts/verify_hw10.py
PYTHONPATH=. .venv/bin/streamlit run code/hw10/dashboard.py --server.port 8510
```

Frozen inputs are in `reports/hw10/data/`. Raw machine-readable outputs are in `reports/hw10/raw/`. Dashboard captures are in `reports/hw10/evidence/`.
