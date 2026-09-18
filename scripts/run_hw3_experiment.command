#!/bin/zsh
set -eu

cd "$(dirname "$0")/.."
HW3_MODEL_CACHE="$PWD/.cache/huggingface"
export HF_HOME="$HW3_MODEL_CACHE"
export HF_HUB_CACHE="$HW3_MODEL_CACHE/hub"
export HF_XET_CACHE="$HW3_MODEL_CACHE/xet"
export HF_HUB_DISABLE_XET=1
exec > >(tee reports/hw03/RUN_LOG.txt) 2>&1

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Started HW3 retrieval comparison"
echo '$ .venv/bin/python scripts/run_hw3_retrieval.py --top-k 5'
.venv/bin/python scripts/run_hw3_retrieval.py --top-k 5
echo '$ .venv/bin/python scripts/generate_hw3_metrics.py'
.venv/bin/python scripts/generate_hw3_metrics.py
echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Finished HW3 retrieval comparison"
