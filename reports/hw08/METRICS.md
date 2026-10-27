# Homework 8 results

## Failure behavior

| Failure scenario | Before fix | After fix |
| --- | --- | --- |
| Duplicate delivery | A replay could create a second entity. | The correlation ID cache returns the original response and entity count remains one. |
| Consumer killed mid-work | Auto-commit could acknowledge unfinished work. | The offset is committed only after the output is published; restart redelivers unfinished work. |
| Poison message | An unbounded retry blocks later messages. | Three attempts are allowed then the record is moved to `s3539_dead_letter`; later messages continue. |
| Two partitions/two consumers | Unkeyed related messages can complete out of order. | The recall entity key maps all 20 messages to one partition in input order. |

## HW2 graph compared with Kafka

Kafka adds independent scaling and decoupled failure recovery. Planner Writer and Reviewer can restart or scale without being called directly by another stage. The tradeoff is that the application must now handle duplicate delivery ordering offset commits retries and dead-letter records explicitly.

