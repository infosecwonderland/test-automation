#!/usr/bin/env python3
"""Fails with exit code 1 if any ERROR-severity Semgrep findings exist."""
import json
import sys

with open("security-tests/semgrep/results.json") as f:
    data = json.load(f)

errors = [
    r for r in data.get("results", [])
    if r.get("extra", {}).get("severity") == "ERROR"
]

if errors:
    print(f"GATE FAILED: {len(errors)} ERROR-severity finding(s):")
    for r in errors:
        print(f"  {r['check_id']} at {r['path']}:{r['start']['line']}")
    sys.exit(1)

print("Semgrep gate passed.")
