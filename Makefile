PYTHON ?= .venv/bin/python
MODEL ?= qwen3:8b

.PHONY: test run-web run-hw2-graph experiment-hw2 metrics-hw2 verify-hw02 run-agent run-client experiment metrics verify-hw01 docker-build docker-run docker-test docker-stop

test:
	$(PYTHON) -m unittest discover -s tests -v

run-web:
	$(PYTHON) -m uvicorn code.web_application.backend:app --host 127.0.0.1 --port 8839

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
