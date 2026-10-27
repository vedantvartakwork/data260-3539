# Homework 8 results

## Failure behavior

| Failure scenario | Before fix | After fix |
| --- | --- | --- |
| Duplicate delivery | A replay could create a second entity. | The correlation ID cache returns the original response and entity count remains one. |
| Consumer killed mid-work | Auto-commit could acknowledge unfinished work. | The offset is committed only after the output is published; restart redelivers unfinished work. |
| Poison message | An unbounded retry blocks later messages. | Three attempts are allowed then the record is moved to `s3539_dead_letter`; later messages continue. |
| Two partitions/two consumers | Unkeyed related messages can complete out of order. | The recall entity key maps all 20 messages to one partition in input order. |

## Live ordering result

- VERIFY_SEED: 263539
- Unkeyed completion: 6 8 1 2 9 3 4 15 5 17 19 7 10 20 11 12 13 14 16 18
- Keyed completion: 1 through 20
- Keyed partitions: [0]

## JMeter direct-endpoint run

| Threads | Ramp (s) | Samples | Passed | Error % | Average (ms) | Min | Max | p95 | Throughput (req/s) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 10 | 100 | 100 | 0.00 | 4.04 | 1 | 15 | 8 | 10.13 |

## HW2 graph compared with Kafka

Kafka adds independent scaling and decoupled failure recovery. Planner Writer and Reviewer can restart or scale without being called directly by another stage. The tradeoff is that the application must now handle duplicate delivery ordering offset commits retries and dead-letter records explicitly.

