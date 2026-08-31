# DATA 260 Homework 1 - SID4 3539

I completed Homework 1 for my assigned domain, Grocery supply and recall notices.

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
