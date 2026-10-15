# DATA 260 Homework 6

Student: Vedant Vartak
SID4: 3539
Local model: `qwen3:8b` through Ollama
Database: MongoDB `s3539_doc`

## Run

```bash
make mongo-hw6-up
make run-hw6-api
```

Open `http://127.0.0.1:8839/docs` for the live OpenAPI interface.

## Verify

```bash
make test-hw6
make experiment-hw6
make verify-hw06
```

The MongoDB-backed CRUD endpoints are under `/api/v1/documents`. Long-term
memory uses `/api/chat`, `/api/memory/{user_id}`, and
`/api/aggregate/{user_id}`. Raw database, endpoint, per-turn, probe, and
file-consolidation evidence is in `reports/hw06/raw/`.
