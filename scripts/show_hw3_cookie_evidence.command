#!/bin/zsh
set -eu

cd "$(dirname "$0")/.."
echo '$ .venv/bin/python scripts/show_hw3_cookie_evidence.py'
.venv/bin/python scripts/show_hw3_cookie_evidence.py
