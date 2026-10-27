# Homework 8 reproduction

```bash
docker compose -f docker-compose.hw8.yml up --build -d
.venv/bin/python -m code.hw8.homework_demo
.venv/bin/python -m code.hw8.send_question
.venv/bin/python scripts/run_hw08_experiments.py
.venv/bin/python -m unittest tests.test_hw08 -v
.venv/bin/python scripts/verify_hw08.py
```

The API is available at `http://127.0.0.1:8839`.

