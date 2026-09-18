# Homework 3 Retrieval Metrics

Model: `sentence-transformers/all-MiniLM-L6-v2`; top-k: `5`; questions: `5`.

| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Semantic | 154 | 3246.10 | 0.7151 | 0.6773 | 100.0% | 7.479 |
| Sentence window | 2934 | 170.38 | 0.8214 | 0.7927 | 100.0% | 31.457 |
| Token | 540 | 1108.32 | 0.7652 | 0.7266 | 100.0% | 11.182 |

Recall@k is the share of questions where at least one of the top-k chunks came from the expected source file.

## Per-question expected-source recall

| Question | Token | Semantic | Sentence window |
| --- | ---: | ---: | ---: |
| q1 | Yes | Yes | Yes |
| q2 | Yes | Yes | Yes |
| q3 | Yes | Yes | Yes |
| q4 | Yes | Yes | Yes |
| q5 | Yes | Yes | Yes |

## Confidently scored wrong retrieval

- Question: q3 - What information should a public food recall warning give consumers so they can identify the product and understand the risk?
- Technique and rank: Token rank 2
- Cosine similarity: 0.7920
- Expected source: `fda_public_warning_guidance.txt`
- Retrieved source: `fda_retail_consignee_lists_guidance.txt`
- Preview: information otherwise exempt from public disclosure, such as CCI, is nevertheless available for public disclosure to the extent necessary to effectuate a recall
- Why it likely scored well: both passages use closely related FDA recall, public-health, and notification vocabulary even though this source does not contain the source-unique answer.
