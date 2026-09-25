# Homework 4 Metrics

Model for Part 4: `qwen3:8b`; SEED: `3539`; VERIFY_SEED: `263539`.

## N+1 query comparison

| Page size | Version | SQL statements/request | p50 (ms) | p95 (ms) | p99 (ms) | Speed-up |
| ---: | :--- | ---: | ---: | ---: | ---: | ---: |
| 10 | naive | 11 | 6.023 | 7.935 | 8.608 | - |
| 10 | fixed | 1 | 3.303 | 8.523 | 25.920 | 1.82x |
| 50 | naive | 51 | 18.035 | 20.308 | 22.296 | - |
| 50 | fixed | 1 | 5.656 | 7.242 | 19.120 | 3.19x |
| 200 | naive | 201 | 59.150 | 72.617 | 74.108 | - |
| 200 | fixed | 1 | 11.273 | 14.457 | 20.258 | 5.25x |

The naive endpoint issues one recall query plus one related-event query per returned record. The fixed endpoint uses eager loading and completes the same response with one SQL statement. The difference grows with page size because the naive query count grows linearly while the fixed query count stays constant.

## Index experiment

| Plan | Access type | Key | Estimated rows |
| :--- | :--- | :--- | ---: |
| Before index | ALL | - | 4967 |
| After index | ref | idx_recall_notices_category | 1188 |

The category filter changed from a full table scan (`ALL`) to indexed reference access (`ref`).

## Grounded RAG evaluation

| Configuration | Correct answers | Grounded answers | Format compliant |
| :--- | ---: | ---: | ---: |
| no_rag | 1/6 | 0/6 | 4/6 |
| basic_rag | 4/6 | 0/6 | 4/6 |
| context_rag | 6/6 | 6/6 | 6/6 |

The context-engineered configuration cited retrieved sources and used the required refusal for both unsupported questions.

### top-k comparison for the two-chunk question

| k | Chunks kept | Correct retrieval | Correct answer |
| ---: | ---: | :---: | :---: |
| 1 | 1 | No | No |
| 3 | 3 | No | No |
| 5 | 5 | Yes | Yes |
