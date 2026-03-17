#!/usr/bin/env python3
"""
convert_to_allure.py
--------------------
Converts Semgrep JSON output to Allure result JSON files.

Each rule becomes one test case in the Allure report:
  - findings exist  → status "failed"  with file:line details
  - no findings     → status "passed"

Usage:
    python3 convert_to_allure.py <semgrep-results.json> <allure-results-dir>
"""

import json
import os
import sys
import time
import uuid
from collections import defaultdict

SEVERITY_MAP = {
    "ERROR": "critical",
    "WARNING": "normal",
    "INFO": "minor",
}


def _write_result(output_dir: str, result: dict):
    path = os.path.join(output_dir, f"{uuid.uuid4()}-result.json")
    with open(path, "w") as fh:
        json.dump(result, fh, indent=2)


def main():
    if len(sys.argv) < 3:
        print("Usage: convert_to_allure.py <results.json> <allure-results-dir>")
        sys.exit(1)

    results_file = sys.argv[1]
    output_dir = sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)

    with open(results_file) as fh:
        data = json.load(fh)

    findings = data.get("results", [])
    now_ms = int(time.time() * 1000)

    # Group findings by rule id
    by_rule: dict = defaultdict(list)
    for finding in findings:
        by_rule[finding["check_id"]].append(finding)

    written = 0

    for rule_id, rule_findings in by_rule.items():
        severity_raw = rule_findings[0].get("extra", {}).get("severity", "WARNING")
        message_lines = []
        for f in rule_findings:
            fpath = f.get("path", "?")
            line = f.get("start", {}).get("line", "?")
            msg = f.get("extra", {}).get("message", "")
            message_lines.append(f"{fpath}:{line} — {msg}")

        _write_result(output_dir, {
            "uuid": str(uuid.uuid4()),
            "testCaseId": rule_id,
            "fullName": f"SAST: {rule_id}",
            "name": rule_id,
            "status": "failed",
            "statusDetails": {
                "message": f"Found {len(rule_findings)} issue(s)",
                "trace": "\n".join(message_lines),
            },
            "labels": [
                {"name": "feature", "value": "SAST"},
                {"name": "story", "value": "Semgrep"},
                {"name": "severity", "value": SEVERITY_MAP.get(severity_raw, "normal")},
            ],
            "start": now_ms,
            "stop": now_ms + 1,
        })
        written += 1

    # Write a single "passed" summary if there were zero findings
    if not by_rule:
        _write_result(output_dir, {
            "uuid": str(uuid.uuid4()),
            "testCaseId": "semgrep-clean",
            "fullName": "SAST: Semgrep — no issues found",
            "name": "Semgrep — no issues found",
            "status": "passed",
            "statusDetails": {"message": "All rules passed with zero findings."},
            "labels": [
                {"name": "feature", "value": "SAST"},
                {"name": "story", "value": "Semgrep"},
            ],
            "start": now_ms,
            "stop": now_ms + 1,
        })
        written += 1

    print(f"Allure results written: {written}  (findings: {len(findings)})")


if __name__ == "__main__":
    main()
