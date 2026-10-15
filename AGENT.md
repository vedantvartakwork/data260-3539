# Homework 6 Durable Agent Instructions

## Inherited HW1 code-review behavior

- Respond to code-review requests using bullet points only.
- Begin review bullets with `BUG:`, `RISK:`, `STYLE:`, or `OK:`.
- Cite a line number when the supplied code includes line numbers.
- Explain the concrete effect of every reported issue and do not invent problems.

## Project

- Reuse the existing DATA 260 repository and shared model adapter; do not create a second application copy.
- Keep SID-derived values deterministic: SID4 3539, PORT_BASE 8839, PREFIX s3539, and VERIFY_SEED 263539.

## Stack and architecture

- Use FastAPI, Pydantic v2, PyMongo, local MongoDB, and the existing local Ollama adapter.
- Keep configuration, persistence, schemas, routes, and orchestration in separate modules.

## Code conventions

- Add type hints and concise docstrings to public Python functions and classes.
- Emit structured JSON and keep stdout free of secrets or database credentials.

## Testing

- Provide deterministic offline tests that never require MongoDB, Ollama, or internet access.
- Run the HW6 verification script before tagging or packaging the submission.

## Prohibited actions

- Never call a hosted language model or put credentials in source control.
- Never delete or overwrite another homework's evidence, reports, or tags.
