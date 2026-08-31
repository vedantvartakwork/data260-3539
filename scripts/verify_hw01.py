#!/usr/bin/env python3
"""Run reproducible checks and write reports/hw01/verification.json."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_FILES = [
    "DOMAIN_SCHEMA.md",
    "Dockerfile",
    "index.html",
    "app.js",
    "agents_demo.py",
    "hw1_client.py",
    "AGENT.md",
    "src/model_client.py",
    "reports/hw01/RUN_LOG.txt",
    "reports/hw01/METRICS.md",
    "reports/hw01/AI_USE.md",
    "reports/hw01/report.pdf",
    "reports/hw01/aws_deployment_evidence.json",
    "reports/hw01/cases/nondeterminism_input.json",
    "README.md",
    "code/agents_demo.py",
    "code/hw1_client.py",
    "code/Dockerfile",
    "code/web_application/index.html",
    "code/web_application/app.js",
    "reports/hw01/reproducible_run_instructions",
]

REQUIRED_SCREENSHOTS = [
    "01-localhost-form.png",
    "02a-short-content-alert.png",
    "02b-terms-alert.png",
    "03-valid-submission-console.png",
    "04a-docker-build-run-http.png",
    "04b-docker-healthy.png",
    "05-agent-pipeline.png",
    "06-nondeterminism-metrics.png",
    "07a-token-stats-turn3.png",
    "07b-token-stats-turn5.png",
    "07a-ecs-service-running.png",
    "07b-aws-public-form.png",
]


def check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "details": details}


def main() -> None:
    checks: list[dict[str, object]] = []
    missing = [path for path in REQUIRED_FILES if not Path(path).is_file()]
    checks.append(check("required_files", not missing, "all required source files present" if not missing else f"missing: {missing}"))

    ai_use_text = Path("reports/hw01/AI_USE.md").read_text(encoding="utf-8") if not missing else ""
    report_path = Path("reports/hw01/report.pdf")
    final_markers_absent = all(
        marker not in ai_use_text.casefold()
        for marker in ("draft:", "personalize", "review and rewrite")
    )
    report_finalized = report_path.is_file() and report_path.stat().st_size > 100_000
    checks.append(check(
        "final_report_and_ai_disclosure",
        final_markers_absent and report_finalized,
        "final PDF and completed AI_USE.md are present",
    ))

    screenshot_dir = Path("reports/hw01/screenshots")
    missing_screenshots = [
        name for name in REQUIRED_SCREENSHOTS
        if not (screenshot_dir / name).is_file() or (screenshot_dir / name).stat().st_size == 0
    ]
    checks.append(check(
        "required_screenshots",
        not missing_screenshots,
        f"captured {len(REQUIRED_SCREENSHOTS)} required screenshots" if not missing_screenshots else f"missing: {missing_screenshots}",
    ))

    aws_evidence_path = Path("reports/hw01/aws_deployment_evidence.json")
    if aws_evidence_path.exists():
        aws_evidence = json.loads(aws_evidence_path.read_text(encoding="utf-8"))
        deployment = aws_evidence.get("deployment", {})
        cleanup = aws_evidence.get("cleanup_verification", {})
        deployed_correctly = (
            aws_evidence.get("account_id") == "243396654546"
            and aws_evidence.get("region") == "us-east-2"
            and deployment.get("desired_count") == 1
            and deployment.get("running_count") == 1
            and deployment.get("pending_count") == 0
            and deployment.get("public_http_status") == 200
        )
        cleaned_up = (
            cleanup.get("cluster_status") == "INACTIVE"
            and cleanup.get("running_tasks") == 0
            and cleanup.get("pending_tasks") == 0
            and cleanup.get("active_services") == 0
            and not cleanup.get("ecr_repository_exists", True)
            and not cleanup.get("log_group_exists", True)
            and not cleanup.get("security_group_exists", True)
            and not cleanup.get("execution_role_exists", True)
        )
        checks.append(check("ecs_deployment_evidence", deployed_correctly, "one-task ECS service and public HTTP 200 captured"))
        checks.append(check("aws_cleanup_evidence", cleaned_up, "temporary ECS, ECR, log, security-group, and IAM resources removed"))
    else:
        checks.append(check("ecs_deployment_evidence", False, "AWS evidence file missing"))
        checks.append(check("aws_cleanup_evidence", False, "AWS evidence file missing"))

    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        capture_output=True,
        text=True,
    )
    checks.append(check("unit_tests", tests.returncode == 0, (tests.stdout + tests.stderr).strip()))
    js_tests = subprocess.run(["node", "tests/test_app_js.mjs"], capture_output=True, text=True)
    checks.append(check("javascript_submission_tests", js_tests.returncode == 0, (js_tests.stdout + js_tests.stderr).strip()))

    raw_path = Path("reports/hw01/raw/nondeterminism_results.json")
    if raw_path.exists():
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        successful = [record for record in raw if record.get("success")]
        temp_counts = {
            "0.7": sum(float(record["temperature"]) == 0.7 and record.get("success") for record in raw),
            "0.0": sum(float(record["temperature"]) == 0.0 and record.get("success") for record in raw),
        }
        valid_shapes = all(
            len(record.get("tags", [])) == 3
            and len({" ".join(tag.casefold().split()) for tag in record["tags"]}) == 3
            and len(record.get("summary", "").split()) <= 25
            for record in successful
        )
        checks.append(check("experiment_40_successes", len(successful) == 40 and temp_counts == {"0.7": 20, "0.0": 20}, str(temp_counts)))
        checks.append(check("experiment_output_shapes", valid_shapes, f"validated {len(successful)} successful outputs"))
    else:
        checks.append(check("experiment_40_successes", False, "raw experiment file does not exist"))
        checks.append(check("experiment_output_shapes", False, "raw experiment file does not exist"))

    model_call_files = []
    forbidden_direct_calls = []
    for path in [Path("agents_demo.py"), Path("hw1_client.py"), *Path("scripts").glob("*.py")]:
        if path.resolve() == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        if "OllamaClient" in text:
            model_call_files.append(str(path))
        if "/api/chat" in text:
            forbidden_direct_calls.append(str(path))
    checks.append(check("model_adapter_only", not forbidden_direct_calls, f"adapter consumers: {model_call_files}"))

    task_template = Path("aws/task-definition.json.tpl").read_text(encoding="utf-8")
    checks.append(check("ecs_desired_count_one", "--desired-count 1" in Path("aws/deploy.sh").read_text(encoding="utf-8"), "deployment script requests exactly one task"))
    checks.append(check("container_port_8839", '"containerPort": 8839' in task_template, "task definition maps PORT_BASE 8839"))

    try:
        with urllib.request.urlopen("http://127.0.0.1:8839/", timeout=5) as response:
            local_page = response.read().decode("utf-8")
        local_http_ok = response.status == 200 and "Grocery Recall Notice" in local_page
        local_http_details = f"HTTP {response.status} from localhost:8839"
    except (urllib.error.URLError, TimeoutError) as exc:
        local_http_ok = False
        local_http_details = f"local container unavailable: {exc}"
    checks.append(check("docker_local_http", local_http_ok, local_http_details))

    automated_passed = all(bool(item["passed"]) for item in checks)
    manual_blockers = [] if automated_passed else ["one or more automated checks failed"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sid4": 3539,
        "verify_seed": 263539,
        "automated_checks_passed": automated_passed,
        "submission_ready": automated_passed,
        "manual_blockers": manual_blockers,
        "checks": checks,
    }
    output = Path("reports/hw01/verification.json")
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if automated_passed else 1)


if __name__ == "__main__":
    main()
