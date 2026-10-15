# Homework 6 Memory Metrics

Mode: `local Ollama qwen3:8b`. Each row uses the same 30-message conversation and five fixed probes.

| Run | N | Summary interval | Top-k episodes | Mean prompt tokens | Mean latency (ms) | Mean probe score (1–5) |
|---|---:|---:|---:|---:|---:|---:|
| window_n4 | 4 | 4 | 3 | 599.233 | 9302.267 | 3.8 |
| window_n12 | 12 | 4 | 3 | 817.933 | 9386.976 | 3.8 |
| window_n30 | 30 | 4 | 3 | 1248 | 14708.965 | 3.8 |
| compact_policy | 4 | 2 | 5 | 616.567 | 7731.462 | 4.6 |

## Cost projection for 10,000 30-turn conversations

Assumptions: input tokens cost $1 per million and output tokens cost $5 per million.
Best measured case (`compact_policy`): **$282.67**.
Worst measured case (`window_n30`): **$469.10**.

## Selection

`compact_policy` is the best setting because it has the lowest measured token-weighted cost and a 4.6/5 probe score. Relative to `window_n30`, it saves **50.6%** of prompt tokens and changes quality by **+0.8 points**. `window_n30` is the worst setting because it has the highest projected cost. The fixed N sweep isolates the context-window tradeoff; the compact-policy row demonstrates controlled eviction plus more frequent compression and retrieval.
