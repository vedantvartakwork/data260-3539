#!/bin/zsh
set -e

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR/.."

docker stop data260-3539-hw1 >/dev/null 2>&1 || true
clear

echo '$ docker build --quiet --tag data260-3539:hw1 .'
docker build --quiet --tag data260-3539:hw1 .

echo '$ docker run --detach --rm --name data260-3539-hw1 -p 8839:8839 data260-3539:hw1'
docker run --detach --rm --name data260-3539-hw1 -p 8839:8839 data260-3539:hw1

echo "$ curl --silent --output /dev/null --write-out 'HTTP status: %{http_code}' http://127.0.0.1:8839/"
curl --silent --output /dev/null --write-out 'HTTP status: %{http_code}\n' http://127.0.0.1:8839/

echo "$ docker ps --filter name=data260-3539-hw1 --format 'table NAMES STATUS PORTS'"
docker ps --filter name=data260-3539-hw1 --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo
echo 'Docker evidence is ready. Keep this window open for the screenshot.'
exec zsh -f
