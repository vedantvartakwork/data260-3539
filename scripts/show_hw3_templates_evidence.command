#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."

echo '$ find code/web_application/templates -maxdepth 1 -type f -print | sort'
find code/web_application/templates -maxdepth 1 -type f -print | sort
