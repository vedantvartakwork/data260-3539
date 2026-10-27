#!/usr/bin/env bash
set -euo pipefail

create_topic() {
  /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server kafka:29092 \
    --create \
    --if-not-exists \
    --topic "$1" \
    --partitions "$2" \
    --replication-factor 1
}

create_topic s3539_entity_requests 1
create_topic s3539_entity_responses 1
create_topic s3539_inbox 1
create_topic s3539_tasks 2
create_topic s3539_drafts 1
create_topic s3539_final 1
create_topic s3539_dead_letter 1

echo "Vedant Vartak - all seven HW8 topics created"
/opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:29092 --list | sort

