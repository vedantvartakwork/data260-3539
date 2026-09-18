"""Run the Homework 3 graded retrieval comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from code.hw3_retrieval import MODEL_NAME, TOP_K, run_comparison


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    args = parser.parse_args()

    run_comparison(
        corpus_dir=ROOT / "reports" / "hw03" / "corpus" / "text",
        questions_path=ROOT / "reports" / "hw03" / "questions.yaml",
        raw_dir=ROOT / "reports" / "hw03" / "raw",
        model_name=args.model,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
