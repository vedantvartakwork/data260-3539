#!/bin/zsh
cd "/Users/vedantvartak/Documents/Codex/2026-08-25/c/outputs/data260-3539" || exit 1
clear
echo '$ grep -E "Started HW2 experiments|Finished HW2 experiments|Finished post-fix" reports/hw02/RUN_LOG.txt'
grep -E "Started HW2 experiments|Finished HW2 experiments|Finished post-fix" reports/hw02/RUN_LOG.txt
echo
echo '$ sed -n '\''1,80p'\'' reports/hw02/METRICS.md'
sed -n '1,80p' reports/hw02/METRICS.md
read -k 1
