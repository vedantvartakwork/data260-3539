#!/bin/zsh
set -eu

cd "$(dirname "$0")/.."
echo '$ .venv/bin/python scripts/show_hw3_session_evidence.py'
.venv/bin/python scripts/show_hw3_session_evidence.py
