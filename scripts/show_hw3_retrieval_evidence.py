"""Display one shared HW3 query for all three retrieval techniques."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "reports" / "hw03" / "raw"
QUESTION_ID = "q3"
TECHNIQUES = ["token", "semantic", "sentence_window"]


def main() -> None:
    print("HOMEWORK 3 - SHARED QUERY RETRIEVAL EVIDENCE")
    for technique in TECHNIQUES:
        path = RAW / f"{QUESTION_ID}_{technique}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        print(f"\nTECHNIQUE: {technique}")
        print(f"Query: {payload['question']}")
        print(
            f"Query embedding: dimension={payload['query_embedding_dim']}, "
            f"first8={payload['query_embedding_first8']}"
        )
        print(
            f"Vector shapes: query={tuple(payload['query_vector_shape'])}, "
            f"documents={tuple(payload['doc_vectors_shape'])}"
        )
        print(f"Retrieval latency: {payload['retrieval_latency_ms']:.3f} ms")
        print("rank  store_score  cosine_sim  chunk_len  source  preview")
        for row in payload["results"]:
            preview = row["preview"][:90]
            print(
                f"{row['rank']:>4}  {row['store_score']:>11.4f}  "
                f"{row['cosine_sim']:>10.4f}  {row['chunk_len']:>9}  "
                f"{row['source_file']}  {preview}"
            )


if __name__ == "__main__":
    main()
