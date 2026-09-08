#!/bin/zsh
cd "/Users/vedantvartak/Documents/Codex/2026-08-25/c/outputs/data260-3539" || exit 1
clear
echo '$ .venv/bin/python hw2_graph.py --input-file reports/hw02/cases/schema_input.json --model qwen3:8b --temperature 0.7 --max-turns 10 --force-review-issue-once --compact-stream --result-file reports/hw02/raw/correction_loop_demo.json'
.venv/bin/python hw2_graph.py --input-file reports/hw02/cases/schema_input.json --model qwen3:8b --temperature 0.7 --max-turns 10 --force-review-issue-once --compact-stream --result-file reports/hw02/raw/correction_loop_demo.json
read -k 1
