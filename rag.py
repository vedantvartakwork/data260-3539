"""Grounded RAG comparison for the Homework 4 grocery-recall corpus."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import MetadataMode
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.model_client import OllamaClient


PROJECT_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = PROJECT_ROOT / "reports/hw03/corpus/text"
QUESTIONS_PATH = PROJECT_ROOT / "reports/hw04/questions.yaml"
RAW_DIR = PROJECT_ROOT / "reports/hw04/raw"
MODEL_CACHE = PROJECT_ROOT / ".cache/huggingface"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "qwen3:8b"
REFUSAL = "I cannot answer this question from the provided documents"

os.environ.setdefault("HF_HOME", str(MODEL_CACHE))
os.environ.setdefault("HF_HUB_CACHE", str(MODEL_CACHE / "hub"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def load_documents() -> list[Document]:
    documents = []
    for path in sorted(CORPUS_DIR.glob("*.txt")):
        document = Document(
            text=path.read_text(encoding="utf-8"),
            metadata={"source": path.name},
        )
        document.excluded_embed_metadata_keys = ["source"]
        documents.append(document)
    if len(documents) < 5:
        raise ValueError("HW4 requires a corpus of at least five documents")
    return documents


def load_questions() -> list[dict[str, Any]]:
    payload = yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = payload.get("questions", [])
    if len(questions) != 6:
        raise ValueError("HW4 requires exactly six evaluation questions")
    return questions


def build_index() -> tuple[VectorStoreIndex, list[Any], HuggingFaceEmbedding]:
    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        cache_folder=str(MODEL_CACHE),
        normalize=True,
        show_progress_bar=False,
    )
    splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(load_documents(), show_progress=False)
    for position, node in enumerate(nodes, start=1):
        source = str(node.metadata.get("source", "unknown"))
        node.metadata["chunk_id"] = f"{Path(source).stem}-{position:04d}"
        node.excluded_embed_metadata_keys = ["source", "chunk_id"]
    storage = StorageContext.from_defaults(vector_store=SimpleVectorStore())
    index = VectorStoreIndex(
        nodes=nodes,
        embed_model=embed_model,
        storage_context=storage,
        show_progress=False,
    )
    return index, nodes, embed_model


def retrieve(index: VectorStoreIndex, question: str, top_k: int) -> list[dict[str, Any]]:
    started = perf_counter()
    matches = index.as_retriever(similarity_top_k=top_k).retrieve(question)
    latency_ms = (perf_counter() - started) * 1000
    rows = []
    for rank, match in enumerate(matches, start=1):
        rows.append(
            {
                "rank": rank,
                "score": round(float(match.score or 0.0), 6),
                "source": str(match.node.metadata.get("source", "unknown")),
                "chunk_id": str(match.node.metadata.get("chunk_id", match.node.node_id)),
                "text": match.node.get_content(metadata_mode=MetadataMode.NONE).strip(),
                "retrieval_latency_ms": round(latency_ms, 3),
            }
        )
    return rows


def normalized_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def near_duplicate(left: str, right: str) -> bool:
    left_words = normalized_words(left)
    right_words = normalized_words(right)
    if not left_words or not right_words:
        return False
    overlap = len(left_words & right_words) / len(left_words | right_words)
    return overlap >= 0.78


def engineer_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk["score"] < 0.35:
            continue
        if any(near_duplicate(chunk["text"], existing["text"]) for existing in kept):
            continue
        kept.append(chunk)
    return kept


def format_context(chunks: list[dict[str, Any]], labels: bool) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        if labels:
            heading = f"[Source {index}: {chunk['source']} | chunk {chunk['chunk_id']}]"
        else:
            heading = f"Chunk {index}"
        blocks.append(f"{heading}\n{chunk['text']}")
    return "\n\n".join(blocks)


def call_model(client: OllamaClient, configuration: str, question: str, chunks: list[dict[str, Any]]) -> str:
    if configuration == "no_rag":
        prompt = f"Answer the following question concisely.\n\nQuestion: {question}"
    elif configuration == "basic_rag":
        prompt = (
            "Use the retrieved text below to answer the question.\n\n"
            f"{format_context(chunks, labels=False)}\n\nQuestion: {question}"
        )
    else:
        context = format_context(chunks, labels=True)
        prompt = (
            "Answer only from the supplied context. Do not use outside knowledge. "
            "Cite supporting evidence with [Source N]. If the context does not explicitly "
            f"support an answer, reply exactly: {REFUSAL}\n\n"
            f"Context:\n{context or '(no relevant context remained)'}\n\n"
            f"Question: {question}"
        )
    result = client.complete(
        [{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return result.content.strip()


def retrieval_is_correct(question: dict[str, Any], chunks: list[dict[str, Any]]) -> bool:
    expected = list(question["expected_sources"])
    if question["should_refuse"]:
        return True
    sources = [chunk["source"] for chunk in chunks]
    if not all(source in sources for source in expected):
        return False
    minimum = int(question.get("minimum_expected_chunks", 1))
    if minimum > 1:
        return sum(source in expected for source in sources) >= minimum
    return True


def answer_is_correct(question: dict[str, Any], answer: str) -> bool:
    if question["should_refuse"]:
        return REFUSAL.lower() in answer.lower()
    lowered = answer.lower()
    return all(keyword.lower() in lowered for keyword in question["expected_keywords"])


def evaluate(question: dict[str, Any], configuration: str, answer: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    correct_retrieval = retrieval_is_correct(question, chunks) if configuration != "no_rag" else None
    correct_answer = answer_is_correct(question, answer)
    refused = REFUSAL.lower() in answer.lower()
    grounded = (
        configuration == "context_rag"
        and correct_answer
        and (refused if question["should_refuse"] else "[source " in answer.lower())
    )
    format_compliant = (
        refused if question["should_refuse"]
        else configuration != "context_rag" or "[source " in answer.lower()
    )
    return {
        "question_id": question["id"],
        "question_type": question["type"],
        "configuration": configuration,
        "correct_retrieval": correct_retrieval,
        "correct_answer": correct_answer,
        "grounded": grounded,
        "refused_when_needed": refused if question["should_refuse"] else None,
        "format_compliant": format_compliant,
        "answer": answer,
    }


def print_retrieval(question: dict[str, Any], chunks: list[dict[str, Any]], top_k: int) -> str:
    lines = [f"QUESTION {question['id']} | top_k={top_k} | {question['question']}"]
    for chunk in chunks:
        preview = " ".join(chunk["text"].split())[:260].rstrip()
        lines.append(
            f"rank={chunk['rank']} score={chunk['score']:.4f} "
            f"source={chunk['source']} chunk_id={chunk['chunk_id']}\n{preview}"
        )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def run() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    questions = load_questions()
    index, nodes, embed_model = build_index()
    client = OllamaClient(model=LLM_MODEL, temperature=0.0, timeout=240.0)

    print("HOMEWORK 4 - GROUNDED RAG COMPARISON")
    print(f"Documents: {len(load_documents())}")
    print(f"Chunks: {len(nodes)} (chunk_size=500, chunk_overlap=50)")
    print(f"Embedding model: {embed_model.model_name}")
    print(f"Local LLM: {LLM_MODEL}")

    results = []
    evaluations = []
    retrieval_logs = []
    for question in questions:
        raw_chunks = retrieve(index, question["question"], 5)
        top_three = raw_chunks[:3]
        engineered = engineer_context(raw_chunks)
        retrieval_text = print_retrieval(question, top_three, 3)
        retrieval_logs.append(retrieval_text)
        print("\n" + retrieval_text)

        configurations = {
            "no_rag": [],
            "basic_rag": top_three,
            "context_rag": engineered,
        }
        for configuration, chunks in configurations.items():
            answer = call_model(client, configuration, question["question"], chunks)
            row = {
                "question_id": question["id"],
                "question_type": question["type"],
                "question": question["question"],
                "configuration": configuration,
                "retrieved_chunks": chunks,
                "answer": answer,
            }
            results.append(row)
            evaluations.append(evaluate(question, configuration, answer, chunks))
            print(f"\n{configuration.upper()} ANSWER\n{answer}")

    sweep_question = questions[1]
    sweep_rows = []
    for top_k in (1, 3, 5):
        chunks = retrieve(index, sweep_question["question"], top_k)
        engineered = engineer_context(chunks)
        answer = call_model(client, "context_rag", sweep_question["question"], engineered)
        sweep_rows.append(
            {
                "question_id": sweep_question["id"],
                "top_k": top_k,
                "retrieved_chunks": chunks,
                "chunks_after_engineering": len(engineered),
                "correct_retrieval": retrieval_is_correct(sweep_question, engineered),
                "answer": answer,
                "correct_answer": answer_is_correct(sweep_question, answer),
            }
        )

    (RAW_DIR / "rag_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8"
    )
    (RAW_DIR / "retrieval_printouts.txt").write_text(
        "\n\n".join(retrieval_logs) + "\n", encoding="utf-8"
    )
    (RAW_DIR / "k_sweep.json").write_text(
        json.dumps(sweep_rows, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(
        RAW_DIR / "evaluation.csv",
        evaluations,
        [
            "question_id",
            "question_type",
            "configuration",
            "correct_retrieval",
            "correct_answer",
            "grounded",
            "refused_when_needed",
            "format_compliant",
            "answer",
        ],
    )
    (RAW_DIR / "evaluation.json").write_text(
        json.dumps(evaluations, indent=2) + "\n", encoding="utf-8"
    )

    print("\nTOP_K SWEEP")
    for row in sweep_rows:
        print(
            f"k={row['top_k']} kept={row['chunks_after_engineering']} "
            f"retrieval_ok={row['correct_retrieval']} answer_ok={row['correct_answer']}"
        )
    print(f"\nSaved raw outputs under {RAW_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    run()


if __name__ == "__main__":
    main()
