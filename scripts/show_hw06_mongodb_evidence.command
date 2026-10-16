#!/bin/zsh
cd '/Users/vedantvartak/Documents/Codex/2026-08-25/c/outputs/data260-3539'
clear
printf '%s\n' '$ docker exec data260-3539-hw6-mongodb mongosh --quiet s3539_doc --eval <collection inspection query>'
cat reports/hw06/raw/mongodb_shell_evidence.txt
printf '\n%s\n' 'Verified live from MongoDB. Close this window when finished.'
exec zsh
