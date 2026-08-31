PYTHON ?= python3.12
MODEL ?= qwen3:8b

.PHONY: test run-agent run-client experiment metrics verify-hw01 docker-build docker-run docker-test docker-stop

test:
	$(PYTHON) -m unittest discover -s tests -v
	node tests/test_app_js.mjs

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
	docker build -t data260-3539:hw1 .

docker-run:
	docker run --detach --rm --name data260-3539-hw1 -p 8839:8839 data260-3539:hw1

docker-test:
	curl --fail --silent --show-error http://127.0.0.1:8839/ >/dev/null

docker-stop:
	docker stop data260-3539-hw1
