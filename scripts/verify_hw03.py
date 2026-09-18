#!/usr/bin/env python3
"""Run Homework 3 checks and write reports/hw03/verification.json."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HW3 = ROOT / "reports" / "hw03"


def result(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "details": details}


def check_manifest() -> tuple[bool, str]:
    manifest_path = HW3 / "CORPUS_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    documents = manifest["documents"]
    problems = []
    for document in documents:
        for prefix in ["source", "text"]:
            relative = document[f"{prefix}_file"]
            path = ROOT / relative
            if not path.is_file():
                problems.append(f"missing {relative}")
                continue
            data = path.read_bytes()
            if len(data) != document[f"{prefix}_bytes"]:
                problems.append(f"size mismatch {relative}")
            if hashlib.sha256(data).hexdigest() != document[f"{prefix}_sha256"]:
                problems.append(f"hash mismatch {relative}")
    return not problems, "all sizes and hashes match" if not problems else "; ".join(problems)


def check_raw_results() -> tuple[bool, str]:
    paths = sorted((HW3 / "raw").glob("q*_*.json"))
    required = {
        "store_score",
        "cosine_sim",
        "chunk_len",
        "preview",
        "source_file",
    }
    problems = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if len(payload.get("results", [])) != 5:
            problems.append(f"{path.name} does not have top 5")
            continue
        if any(not required.issubset(row) for row in payload["results"]):
            problems.append(f"{path.name} is missing result fields")
        if payload.get("query_embedding_dim") != 384:
            problems.append(f"{path.name} has wrong embedding dimension")
    passed = len(paths) == 15 and not problems
    details = f"{len(paths)}/15 per-query files"
    if problems:
        details += "; " + "; ".join(problems)
    return passed, details


def main() -> None:
    checks: list[dict[str, object]] = []
    required_files = [
        "code/web_application/routers/auth.py",
        "code/web_application/templates/index.html",
        "code/web_application/templates/login.html",
        "code/web_application/templates/dashboard.html",
        "code/hw3_retrieval.py",
        "reports/hw03/questions.yaml",
        "reports/hw03/SOURCES.md",
        "reports/hw03/CORPUS_MANIFEST.json",
        "reports/hw03/RUN_LOG.txt",
        "reports/hw03/METRICS.md",
        "reports/hw03/raw/retrieval_results.csv",
        "reports/hw03/raw/retrieval_results.jsonl",
        "reports/hw03/reproducible_run_instructions",
    ]
    missing = [path for path in required_files if not (ROOT / path).is_file()]
    checks.append(
        result(
            "required_files",
            not missing,
            "all required technical files present" if not missing else f"missing: {missing}",
        )
    )

    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    test_output = (tests.stdout + tests.stderr).strip()
    checks.append(result("unit_tests", tests.returncode == 0, test_output[-5000:]))

    corpus_files = sorted((HW3 / "corpus" / "text").glob("*.txt"))
    corpus_bytes = sum(path.stat().st_size for path in corpus_files)
    checks.append(
        result(
            "graded_corpus",
            len(corpus_files) == 5 and corpus_bytes >= 200_000,
            f"{len(corpus_files)} files; {corpus_bytes} bytes",
        )
    )

    manifest_ok, manifest_details = check_manifest()
    checks.append(result("corpus_manifest", manifest_ok, manifest_details))

    questions = yaml.safe_load((HW3 / "questions.yaml").read_text(encoding="utf-8"))[
        "questions"
    ]
    unique_count = sum(bool(item.get("source_unique")) for item in questions)
    checks.append(
        result(
            "fixed_questions",
            len(questions) == 5 and unique_count >= 2,
            f"{len(questions)} questions; {unique_count} source-unique",
        )
    )

    raw_ok, raw_details = check_raw_results()
    checks.append(result("retrieval_outputs", raw_ok, raw_details))

    run_log = (HW3 / "RUN_LOG.txt").read_text(encoding="utf-8")
    log_ok = "Finished HW3 retrieval comparison" in run_log and "Traceback" not in run_log
    checks.append(result("completed_run_log", log_ok, "clean completed run recorded"))

    metrics = (HW3 / "METRICS.md").read_text(encoding="utf-8")
    metrics_ok = all(
        label in metrics for label in ["Token", "Semantic", "Sentence window", "Confidently scored wrong retrieval"]
    )
    checks.append(result("metrics_table", metrics_ok, "three techniques and wrong retrieval recorded"))

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    passed = all(bool(check["passed"]) for check in checks)
    output = {
        "homework": 3,
        "sid4": 3539,
        "domain_id": 3,
        "port_base": 8839,
        "seed": 3539,
        "verify_seed": 263539,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "commit_hash_at_verification": commit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "passed": passed,
    }
    destination = HW3 / "verification.json"
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
