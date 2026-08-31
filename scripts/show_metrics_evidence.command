#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR/.."
clear

echo "$ grep 'Finished experiment' reports/hw01/RUN_LOG.txt"
grep 'Finished experiment' reports/hw01/RUN_LOG.txt

echo
echo "$ sed -n '9,22p' reports/hw01/METRICS.md"
sed -n '9,22p' reports/hw01/METRICS.md

echo
echo 'Metrics evidence is ready. Keep this window open for the screenshot.'
exec zsh -f
