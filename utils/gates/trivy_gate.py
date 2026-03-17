#!/usr/bin/env python3
"""Fails with exit code 1 if any HIGH or CRITICAL CVEs are found by Trivy."""
import json
import sys

BLOCKING = {"HIGH", "CRITICAL"}

with open("security-tests/trivy/results.json") as f:
    data = json.load(f)

findings = [
    f"{v['VulnerabilityID']} ({v['Severity']}) in {v['PkgName']}@{v['InstalledVersion']}"
    for r in data.get("Results", [])
    for v in (r.get("Vulnerabilities") or [])
    if v.get("Severity", "").upper() in BLOCKING
]

if findings:
    print(f"GATE FAILED: {len(findings)} HIGH/CRITICAL CVE(s):")
    for f in findings:
        print(f"  {f}")
    sys.exit(1)

print("Trivy gate passed.")
