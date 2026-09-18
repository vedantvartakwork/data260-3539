#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
clear
echo '$ .venv/bin/python scripts/show_hw3_retrieval_evidence.py'
.venv/bin/python scripts/show_hw3_retrieval_evidence.py
