PYTHON ?= .venv/bin/python
MODEL ?= qwen3:8b

.PHONY: test run-web mysql-hw4-up mysql-hw4-down seed-hw4 run-hw4-api run-hw4-client experiment-hw4 metrics-hw4 rag-hw4 verify-hw04 warmup-hw3 experiment-hw3 metrics-hw3 verify-hw03 run-hw2-graph experiment-hw2 metrics-hw2 verify-hw02 run-agent run-client experiment metrics verify-hw01 docker-build docker-run docker-test docker-stop

test:
	$(PYTHON) -m unittest discover -s tests -v

run-web:
	SESSION_HTTPS_ONLY=false $(PYTHON) -m uvicorn code.web_application.backend:app --host 127.0.0.1 --port 8839

mysql-hw4-up:
	docker compose -f docker-compose.hw4.yml up -d

mysql-hw4-down:
	docker compose -f docker-compose.hw4.yml down

seed-hw4:
	$(PYTHON) scripts/seed_hw04.py

run-hw4-api:
	SESSION_HTTPS_ONLY=false SESSION_COOKIE_SECURE=false $(PYTHON) -m uvicorn code.web_application.backend:app --host 127.0.0.1 --port 8839

run-hw4-client:
	npm --prefix code/web_application/frontend run dev

experiment-hw4:
	$(PYTHON) scripts/run_hw4_nplus1_experiment.py
	$(PYTHON) scripts/run_hw4_explain.py

metrics-hw4:
	$(PYTHON) scripts/generate_hw4_metrics.py

rag-hw4:
	OLLAMA_SEED=3539 $(PYTHON) rag.py

verify-hw04:
	$(PYTHON) scripts/verify_hw04.py

warmup-hw3:
	$(PYTHON) scripts/run_hw3_warmup.py

experiment-hw3:
	./scripts/run_hw3_experiment.command

metrics-hw3:
	$(PYTHON) scripts/generate_hw3_metrics.py

verify-hw03:
	$(PYTHON) scripts/verify_hw03.py

run-hw2-graph:
	$(PYTHON) hw2_graph.py --input-file reports/hw02/cases/schema_input.json --model $(MODEL) --temperature 0.7 --max-turns 10

experiment-hw2:
	$(PYTHON) scripts/run_hw2_experiments.py

metrics-hw2:
	$(PYTHON) scripts/generate_hw2_metrics.py

verify-hw02:
	$(PYTHON) scripts/verify_hw02.py

run-agent:
	$(PYTHON) agents_demo.py --input-file reports/hw01/cases/nondeterminism_input.json --model $(MODEL) --temperature 0.0

run-client:
	$(PYTHON) hw1_client.py --model $(MODEL)

experiment:
	$(PYTHON) scripts/run_experiment.py --runs 20 --model $(MODEL)

metrics:
	$(PYTHON) scripts/generate_metrics.py

verify-hw01:
	$(PYTHON) scripts/verify_hw01.py

docker-build:
	docker build -t data260-3539:hw2 .

docker-run:
	docker run --detach --rm --name data260-3539-hw2 -p 8839:8839 data260-3539:hw2

docker-test:
	curl --fail --silent --show-error http://127.0.0.1:8839/ >/dev/null

docker-stop:
	docker stop data260-3539-hw2
