# DATA 260 Homework Portfolio - SID4 3539

This repository contains the shared application and report evidence for my DATA 260 homework. My assigned domain is grocery supply and recall notices. Homework-specific results are stored under `reports/hw01/` through `reports/hw05/`; the application code remains in the shared root-level `code/` and `src/` folders.

## My configuration

| Value | Result |
| --- | --- |
| SID4 | `3539` |
| PORT_BASE | `8839` |
| PREFIX | `s3539` |
| SEED | `3539` |
| VERIFY_SEED | `263539` |
| DOMAIN_ID | `3` |
| Hardware | Apple M4 MacBook Air, 10 CPU cores, 16 GB memory |
| Local model | `qwen3:8b` |
| AWS region | `us-east-2` |

## Homework 5

Homework 5 cumulatively extends the HW4 FastAPI/MySQL/React system with manufacturer relationships, Redux Toolkit and Axios, two MCP servers, tested tool contracts, bounded retries, and a safe local-Ollama agent loop.

```bash
make mysql-hw5-up
make seed-hw5
make run-hw5-api
make run-hw5-client
```

The API runs at <http://127.0.0.1:8839>, the React client at <http://127.0.0.1:5173>, and the demo login is `admin@example.edu` / `password`. Run the reproducible evidence commands with:

```bash
make test-hw5
make experiment-hw5
.venv/bin/python scripts/run_hw05_api_integration.py
.venv/bin/python scripts/run_hw05_agent_scenarios.py
make verify-hw05
```

Start the MCP Inspector with either `mcp dev mcp_servers/meals_server.py` or `mcp dev mcp_servers/domain_server.py`. The Postman collection and environment are in `reports/hw05/postman/`.

## Homework 4

Homework 4 adds the cumulative MySQL database, authenticated FastAPI API, React CRUD client, N+1/eager-loading measurements, index experiments, and grounded local RAG evaluation. Its evidence is under `reports/hw04/`.

## Homework 3

Homework 3 adds login, logout, protected routes, secure session settings, an idle timeout, and a retrieval-only comparison of three LlamaIndex chunking methods.

### Run the authenticated FastAPI application

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make run-web
```

Open <http://localhost:8839>. The demo login is `admin` / `password`. The local command disables the cookie's HTTPS-only setting so the browser can use the session on localhost; the application default keeps the Secure attribute enabled.

### Reproduce the Homework 3 retrieval results

```bash
make warmup-hw3
make experiment-hw3
make metrics-hw3
make verify-hw03
```

The graded comparison uses the five fixed questions in `reports/hw03/questions.yaml`, the five FDA source documents recorded in `reports/hw03/SOURCES.md`, and `sentence-transformers/all-MiniLM-L6-v2`. Raw per-query results are stored in `reports/hw03/raw/`.

## Homework 2

Homework 2 extends the grocery-recall application with a responsive interface, a FastAPI CRUD/search backend, and a stateful LangGraph Planner/Reviewer/Supervisor workflow.

### Run the responsive FastAPI application

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make run-web
```

Open <http://localhost:8839>. The application supports creating records, updating ID 1, deleting the highest ID, and searching by product or brand.

### Run the stateful graph

Make sure Ollama is running with `qwen3:8b`, then run:

```bash
make run-hw2-graph
```

All model calls from the Planner and Reviewer go through `src/model_client.py`. The graph streams Supervisor, Planner, and Reviewer updates and uses a bounded correction loop.

### Reproduce the Homework 2 evidence

```bash
make test
make experiment-hw2
make metrics-hw2
make verify-hw02
```

The raw JSON/CSV experiment results, timestamps, metrics, AI-use statement, report, and verification output are in `reports/hw02/`.

## Homework 1

Homework 1 established the original grocery-recall interface, local sequential agents, token-accounting client, and AWS ECS deployment evidence.

## How I ran the web application with Docker

I built the Docker image, started the container and checked that the application returned HTTP status 200.

```bash
make docker-build
make docker-run
make docker-test
```

I opened the application at <http://localhost:8839>. When I finished, I stopped the container.

```bash
make docker-stop
```

## How I ran the Planner, Reviewer and Finalizer

I started Ollama and made sure the `qwen3:8b` model was available.

```bash
ollama serve
ollama pull qwen3:8b
```

I ran the fixed grocery-recall case with this command:

```bash
python3.12 agents_demo.py --input-file reports/hw01/cases/nondeterminism_input.json --model qwen3:8b --temperature 0.0
```

## How I ran the non-determinism experiment

I ran the same saved input 20 times at temperature 0.7 and 20 times at temperature 0.0.

```bash
make experiment
```

The command saved the raw JSON and CSV results in `reports/hw01/raw/`, updated `RUN_LOG.txt` and generated `METRICS.md`.

## How I ran the token-accounting client

I started the interactive client with:

```bash
make run-client
```

I used `/stats` to display the turn count, cumulative token counts and serialized conversation-history length without changing the history. I reproduced the five-turn demonstration with:

```bash
python3.12 scripts/run_five_turn_demo.py
```

## How I verified the project

I ran the self-check with:

```bash
make verify-hw01
```

The command runs the project checks and writes the result to `reports/hw01/verification.json`.

## How I deployed and removed the AWS resources

I deployed one ECS Fargate task in `us-east-2` with:

```bash
CONFIRM_DEPLOY=yes ./aws/deploy.sh
```

After I captured the required evidence, I removed the homework resources with:

```bash
CONFIRM_CLEANUP=yes ./aws/cleanup.sh
```

## Part 4 conceptual answers

### Why is prior context resent?

A chat model does not automatically remember separate API calls. The application resends earlier messages so the model has the context needed to understand the current request.

### System prompt versus user message

A system prompt defines the model's overall role, rules, and response style and has higher priority. A user message contains the individual request being made during the conversation.

### Why do input tokens grow?

Input tokens increase because every new request contains the latest message plus more of the previous conversation. The model must process that growing history again during each turn.

### What limits the growth?

Growth is eventually limited by the model's maximum context window. When the history approaches that limit, older material must be removed, summarized or moved into a new conversation.
