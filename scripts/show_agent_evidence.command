#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR/.."
clear

echo '$ python3.12 agents_demo.py --input-file reports/hw01/cases/nondeterminism_input.json --model qwen3:8b --temperature 0.0'
python3.12 agents_demo.py \
  --input-file reports/hw01/cases/nondeterminism_input.json \
  --model qwen3:8b \
  --temperature 0.0

echo
echo 'Agent evidence is ready. Keep this window open for screenshots.'
exec zsh -f
