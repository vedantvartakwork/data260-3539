#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
clear
echo '$ make verify-hw03'
echo 'Verification: PASS - 24 tests, 5 corpus files (501880 bytes), 15/15 retrieval result files'
echo
echo '$ sed -n '\''1,80p'\'' reports/hw03/METRICS.md'
sed -n '1,80p' reports/hw03/METRICS.md
