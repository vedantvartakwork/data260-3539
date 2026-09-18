"""Retrieval-only comparison for the three Homework 3 chunking methods."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any

# Keep downloaded model files inside this project so the run is reproducible.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_CACHE = PROJECT_ROOT / ".cache" / "huggingface"
os.environ.setdefault("HF_HOME", str(MODEL_CACHE))
os.environ.setdefault("HF_HUB_CACHE", str(MODEL_CACHE / "hub"))
os.environ.setdefault("HF_XET_CACHE", str(MODEL_CACHE / "xet"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

import numpy as np
import pandas as pd
import yaml
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import (
    SemanticSplitterNodeParser,
    SentenceWindowNodeParser,
    TokenTextSplitter,
)
from llama_index.core.schema import MetadataMode
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 5


def load_documents(corpus_dir: Path) -> list[Document]:
    documents = []
    for path in sorted(corpus_dir.glob("*.txt")):
        document = Document(
            text=path.read_text(encoding="utf-8"),
            metadata={"file_name": path.name, "source_path": str(path)},
        )
        # File paths are useful for scoring recall, but not useful embedding text.
        document.excluded_embed_metadata_keys = ["file_name", "source_path"]
        document.excluded_llm_metadata_keys = ["source_path"]
        documents.append(document)
    if not documents:
        raise FileNotFoundError(f"No text documents found under {corpus_dir}")
    return documents


def load_questions(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    if len(questions) != 5:
        raise ValueError("questions.yaml must contain exactly five graded questions")
    return questions


def make_embedding_model(model_name: str = MODEL_NAME) -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(
        model_name=model_name,
        cache_folder=str(MODEL_CACHE),
        normalize=True,
        show_progress_bar=False,
    )


def build_nodes(
    documents: list[Document], embed_model: HuggingFaceEmbedding
) -> dict[str, list[Any]]:
    chunkers = {
        "token": TokenTextSplitter(chunk_size=256, chunk_overlap=40),
        "semantic": SemanticSplitterNodeParser(
            embed_model=embed_model,
            buffer_size=1,
            breakpoint_percentile_threshold=95,
        ),
        "sentence_window": SentenceWindowNodeParser.from_defaults(
            window_size=2,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        ),
    }
    return {
        name: chunker.get_nodes_from_documents(documents, show_progress=False)
        for name, chunker in chunkers.items()
    }


def build_index(nodes: list[Any], embed_model: HuggingFaceEmbedding) -> VectorStoreIndex:
    storage_context = StorageContext.from_defaults(vector_store=SimpleVectorStore())
    return VectorStoreIndex(
        nodes=nodes,
        embed_model=embed_model,
        storage_context=storage_context,
        show_progress=False,
    )


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def chunk_text(node: Any) -> str:
    return node.get_content(metadata_mode=MetadataMode.NONE)


def retrieve_one(
    *,
    technique: str,
    question: dict[str, Any],
    index: VectorStoreIndex,
    nodes: list[Any],
    embed_model: HuggingFaceEmbedding,
    top_k: int,
) -> dict[str, Any]:
    query = question["question"]
    query_vector = np.asarray(embed_model.get_query_embedding(query), dtype=np.float32)

    retriever = index.as_retriever(similarity_top_k=min(top_k, len(nodes)))
    started = perf_counter()
    retrieved = retriever.retrieve(query)
    latency_ms = (perf_counter() - started) * 1000

    texts = [chunk_text(item.node) for item in retrieved]
    doc_vectors = np.asarray(
        embed_model.get_text_embedding_batch(texts), dtype=np.float32
    )

    rows = []
    for rank, (item, text, vector) in enumerate(
        zip(retrieved, texts, doc_vectors, strict=True), start=1
    ):
        source_file = str(item.node.metadata.get("file_name", "unknown"))
        rows.append(
            {
                "rank": rank,
                "store_score": float(item.score) if item.score is not None else None,
                "cosine_sim": cosine_similarity(query_vector, vector),
                "chunk_len": len(text),
                "source_file": source_file,
                "contains_expected_source": source_file
                == question["expected_source_file"],
                "preview": " ".join(text.split())[:160].rstrip(),
            }
        )

    node_lengths = [
        len(chunk_text(node))
        for node in nodes
    ]
    return {
        "question_id": question["id"],
        "question": query,
        "expected_answer": question["expected_answer"],
        "expected_source_file": question["expected_source_file"],
        "source_unique": bool(question.get("source_unique", False)),
        "technique": technique,
        "model": embed_model.model_name,
        "top_k": top_k,
        "query_embedding_dim": int(query_vector.shape[0]),
        "query_embedding_first8": [round(float(value), 6) for value in query_vector[:8]],
        "query_vector_shape": list(query_vector.shape),
        "doc_vectors_shape": list(doc_vectors.shape),
        "retrieval_latency_ms": round(latency_ms, 3),
        "chunk_count": len(nodes),
        "avg_chunk_length": round(float(np.mean(node_lengths)), 2),
        "results": rows,
    }


def print_result(payload: dict[str, Any]) -> None:
    print()
    print(f"TECHNIQUE: {payload['technique']}")
    print(f"QUESTION: {payload['question_id']} - {payload['question']}")
    print(
        "Query embedding: "
        f"dimension={payload['query_embedding_dim']}, "
        f"first8={payload['query_embedding_first8']}"
    )
    print(
        f"Vector shapes: query={tuple(payload['query_vector_shape'])}, "
        f"documents={tuple(payload['doc_vectors_shape'])}"
    )
    print(f"Retrieval latency: {payload['retrieval_latency_ms']:.3f} ms")
    table = pd.DataFrame(payload["results"])[
        ["rank", "store_score", "cosine_sim", "chunk_len", "source_file", "preview"]
    ]
    print(table.to_string(index=False, max_colwidth=58))


def save_results(payloads: list[dict[str, Any]], raw_dir: Path) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)

    for payload in payloads:
        filename = f"{payload['question_id']}_{payload['technique']}.json"
        (raw_dir / filename).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    jsonl_path = raw_dir / "retrieval_results.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for payload in payloads:
            handle.write(json.dumps(payload) + "\n")

    csv_rows = []
    for payload in payloads:
        for result in payload["results"]:
            csv_rows.append(
                {
                    "question_id": payload["question_id"],
                    "technique": payload["technique"],
                    "retrieval_latency_ms": payload["retrieval_latency_ms"],
                    "chunk_count": payload["chunk_count"],
                    "avg_chunk_length": payload["avg_chunk_length"],
                    **result,
                }
            )
    with (raw_dir / "retrieval_results.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(csv_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(csv_rows)


def run_comparison(
    *,
    corpus_dir: Path,
    questions_path: Path,
    raw_dir: Path,
    model_name: str = MODEL_NAME,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    documents = load_documents(corpus_dir)
    questions = load_questions(questions_path)
    embed_model = make_embedding_model(model_name)
    nodes_by_technique = build_nodes(documents, embed_model)

    print("HOMEWORK 3 - RETRIEVAL-ONLY CHUNKING COMPARISON")
    print(f"Model: {model_name}")
    print(f"Documents: {len(documents)}")
    print(f"Questions: {len(questions)}")
    print(f"Top-k: {top_k}")

    payloads = []
    for technique, nodes in nodes_by_technique.items():
        print(f"\nBuilding {technique} index from {len(nodes)} chunks...")
        index = build_index(nodes, embed_model)
        for question in questions:
            payload = retrieve_one(
                technique=technique,
                question=question,
                index=index,
                nodes=nodes,
                embed_model=embed_model,
                top_k=top_k,
            )
            payloads.append(payload)
            print_result(payload)

    save_results(payloads, raw_dir)
    return payloads
