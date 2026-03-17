#!/usr/bin/env python3
"""
convert_to_allure.py
--------------------
Converts security scanner JSON output to Allure result JSON files.

Supported scanners (--type):
  semgrep   Semgrep SAST output  (results[].check_id grouping)
  trivy     Trivy SCA output     (Results[].Vulnerabilities grouping)

Each rule / target becomes one test case:
  - findings exist  → status "failed"  with details
  - no findings     → status "passed"

Usage:
    python3 convert_to_allure.py --type semgrep <results.json> <allure-results-dir>
    python3 convert_to_allure.py --type trivy   <results.json> <allure-results-dir>
"""

import argparse
import json
import os
import sys
import time
import uuid
from collections import defaultdict

SEMGREP_SEVERITY_MAP = {
    "ERROR": "critical",
    "WARNING": "normal",
    "INFO": "minor",
}

TRIVY_SEVERITY_MAP = {
    "CRITICAL": "blocker",
    "HIGH": "critical",
    "MEDIUM": "normal",
    "LOW": "minor",
    "UNKNOWN": "trivial",
}


def _write_result(output_dir: str, result: dict):
    path = os.path.join(output_dir, f"{uuid.uuid4()}-result.json")
    with open(path, "w") as fh:
        json.dump(result, fh, indent=2)


def _convert_semgrep(data: dict, output_dir: str, now_ms: int) -> int:
    findings = data.get("results", [])
    by_rule: dict = defaultdict(list)
    for finding in findings:
        by_rule[finding["check_id"]].append(finding)

    written = 0
    for rule_id, rule_findings in by_rule.items():
        severity_raw = rule_findings[0].get("extra", {}).get("severity", "WARNING")
        lines = []
        for f in rule_findings:
            fpath = f.get("path", "?")
            line = f.get("start", {}).get("line", "?")
            msg = f.get("extra", {}).get("message", "")
            lines.append(f"{fpath}:{line} — {msg}")

        _write_result(output_dir, {
            "uuid": str(uuid.uuid4()),
            "testCaseId": rule_id,
            "fullName": f"SAST: {rule_id}",
            "name": rule_id,
            "status": "failed",
            "statusDetails": {
                "message": f"Found {len(rule_findings)} issue(s)",
                "trace": "\n".join(lines),
            },
            "labels": [
                {"name": "feature", "value": "SAST"},
                {"name": "story", "value": "Semgrep"},
                {"name": "severity", "value": SEMGREP_SEVERITY_MAP.get(severity_raw, "normal")},
            ],
            "start": now_ms,
            "stop": now_ms + 1,
        })
        written += 1

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

    print(f"[semgrep] Allure results written: {written}  (findings: {len(findings)})")
    return written


def _trivy_top_severity(vulns: list) -> str:
    order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    found = {v.get("Severity", "UNKNOWN").upper() for v in vulns}
    for level in order:
        if level in found:
            return TRIVY_SEVERITY_MAP.get(level, "normal")
    return "normal"


def _convert_trivy(data: dict, output_dir: str, now_ms: int) -> int:
    scan_results = data.get("Results", [])
    written = 0
    total_vulns = 0

    for result in scan_results:
        target = result.get("Target", "unknown")
        vulns = result.get("Vulnerabilities") or []
        total_vulns += len(vulns)

        if vulns:
            lines = []
            for v in vulns:
                cve = v.get("VulnerabilityID", "?")
                pkg = v.get("PkgName", "?")
                installed = v.get("InstalledVersion", "?")
                fixed = v.get("FixedVersion", "not fixed")
                severity = v.get("Severity", "UNKNOWN")
                title = (v.get("Title") or v.get("Description", ""))[:120]
                lines.append(f"[{severity}] {cve} — {pkg}@{installed} (fix: {fixed}) {title}")

            _write_result(output_dir, {
                "uuid": str(uuid.uuid4()),
                "testCaseId": f"trivy-{target}",
                "fullName": f"SCA: {target}",
                "name": f"Trivy: {target}",
                "status": "failed",
                "statusDetails": {
                    "message": f"Found {len(vulns)} CVE(s) in {target}",
                    "trace": "\n".join(lines),
                },
                "labels": [
                    {"name": "feature", "value": "SCA"},
                    {"name": "story", "value": "Trivy"},
                    {"name": "severity", "value": _trivy_top_severity(vulns)},
                ],
                "start": now_ms,
                "stop": now_ms + 1,
            })
        else:
            _write_result(output_dir, {
                "uuid": str(uuid.uuid4()),
                "testCaseId": f"trivy-{target}",
                "fullName": f"SCA: {target}",
                "name": f"Trivy: {target}",
                "status": "passed",
                "statusDetails": {"message": "No vulnerabilities found."},
                "labels": [
                    {"name": "feature", "value": "SCA"},
                    {"name": "story", "value": "Trivy"},
                ],
                "start": now_ms,
                "stop": now_ms + 1,
            })

        written += 1

    if not scan_results:
        _write_result(output_dir, {
            "uuid": str(uuid.uuid4()),
            "testCaseId": "trivy-clean",
            "fullName": "SCA: Trivy — no targets scanned",
            "name": "Trivy — no targets scanned",
            "status": "passed",
            "statusDetails": {"message": "Trivy found no scannable targets."},
            "labels": [
                {"name": "feature", "value": "SCA"},
                {"name": "story", "value": "Trivy"},
            ],
            "start": now_ms,
            "stop": now_ms + 1,
        })
        written += 1

    print(f"[trivy] Allure results written: {written}  (CVEs: {total_vulns})")
    return written


def main():
    parser = argparse.ArgumentParser(description="Convert scanner JSON to Allure results")
    parser.add_argument("--type", required=True, choices=["semgrep", "trivy"],
                        help="Scanner type")
    parser.add_argument("results_file", help="Path to scanner JSON output")
    parser.add_argument("output_dir", help="Allure results directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    with open(args.results_file) as fh:
        data = json.load(fh)

    now_ms = int(time.time() * 1000)

    if args.type == "semgrep":
        _convert_semgrep(data, args.output_dir, now_ms)
    else:
        _convert_trivy(data, args.output_dir, now_ms)


if __name__ == "__main__":
    main()
