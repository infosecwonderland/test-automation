"""
failure_analyzer.py
-------------------
Runs a pytest test suite, captures failures, then sends them to Claude
for AI-driven root cause analysis and fix suggestions.

Usage:
    python ai-tests/test-generation/failure_analyzer.py
    python ai-tests/test-generation/failure_analyzer.py --suite api-tests/pytest
    python ai-tests/test-generation/failure_analyzer.py --suite ai-tests/test-generation/generated
    python ai-tests/test-generation/failure_analyzer.py --report-only path/to/report.json
    python ai-tests/test-generation/failure_analyzer.py --output analysis.json
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

import anthropic

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")

# Default suite to analyse when none is specified
DEFAULT_SUITE = os.path.join(GENERATED_DIR)


# ---------------------------------------------------------------------------
# Step 1 – run pytest and collect failures via JSON report
# ---------------------------------------------------------------------------

def run_pytest(suite_path: str, allure_dir=None) -> dict:
    """Run pytest on suite_path and return the parsed JSON report."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        report_path = tmp.name

    cmd = [
        sys.executable, "-m", "pytest",
        suite_path,
        "--tb=long",
        "--json-report",
        f"--json-report-file={report_path}",
        "-q",
    ]

    if allure_dir:
        os.makedirs(allure_dir, exist_ok=True)
        cmd += [f"--alluredir={allure_dir}"]

    print(f"[failure_analyzer] Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if not os.path.isfile(report_path):
        print("[failure_analyzer] WARNING: JSON report not produced — pytest-json-report may not be installed.")
        print("[failure_analyzer] Falling back to text output parsing.")
        return _parse_text_output(result.stdout + result.stderr, suite_path)

    with open(report_path) as f:
        report = json.load(f)
    os.unlink(report_path)
    return report


def _parse_text_output(output: str, suite_path: str) -> dict:
    """Fallback: build a minimal report structure from pytest text output."""
    tests = []
    lines = output.splitlines()
    current_failure = None

    for line in lines:
        if " FAILED" in line:
            name = line.split(" FAILED")[0].strip()
            current_failure = {"nodeid": name, "outcome": "failed", "longrepr": ""}
            tests.append(current_failure)
        elif " PASSED" in line:
            name = line.split(" PASSED")[0].strip()
            tests.append({"nodeid": name, "outcome": "passed", "longrepr": ""})
        elif " ERROR" in line and "::" in line:
            name = line.split(" ERROR")[0].strip()
            current_failure = {"nodeid": name, "outcome": "error", "longrepr": ""}
            tests.append(current_failure)
        elif current_failure and line.startswith(("E ", "  E ", "FAILED", "AssertionError")):
            current_failure["longrepr"] += line + "\n"

    passed = sum(1 for t in tests if t["outcome"] == "passed")
    failed = sum(1 for t in tests if t["outcome"] in ("failed", "error"))

    return {
        "summary": {"passed": passed, "failed": failed, "total": len(tests)},
        "tests": tests,
        "_raw_output": output,
    }


# ---------------------------------------------------------------------------
# Step 2 – extract failures from the report
# ---------------------------------------------------------------------------

def extract_failures(report: dict) -> list[dict]:
    """Return a list of failure dicts with name, error, and traceback."""
    failures = []

    tests = report.get("tests", [])
    for t in tests:
        outcome = t.get("outcome", "")
        if outcome not in ("failed", "error"):
            continue

        # pytest-json-report structure
        longrepr = ""
        call = t.get("call", {})
        if call:
            longrepr = call.get("longrepr", "")
        if not longrepr:
            longrepr = t.get("longrepr", "")

        failures.append({
            "test": t.get("nodeid", t.get("name", "unknown")),
            "outcome": outcome,
            "error": longrepr[:3000],  # cap to avoid huge prompts
        })

    return failures


# ---------------------------------------------------------------------------
# Step 3 – send to Claude for analysis
# ---------------------------------------------------------------------------

def analyze_failures(failures: list[dict], summary: dict) -> dict:
    """Send failures to Claude and return structured analysis."""
    if not failures:
        return {
            "summary": "All tests passed — no failures to analyze.",
            "failure_count": 0,
            "analyses": [],
            "patterns": [],
            "recommendations": [],
        }

    client = anthropic.Anthropic()

    failures_json = json.dumps(failures, indent=2)
    total = summary.get("total", "?")
    passed = summary.get("passed", "?")
    failed = summary.get("failed", len(failures))

    prompt = f"""You are a senior test automation engineer performing AI-driven failure analysis.

Test run summary:
- Total tests: {total}
- Passed: {passed}
- Failed: {failed}

Failed tests (with error details):
{failures_json}

Analyse the failures and respond with a JSON object (no markdown fences) with this exact structure:
{{
  "summary": "<one paragraph summarising what went wrong overall>",
  "failure_count": {failed},
  "analyses": [
    {{
      "test": "<test name>",
      "root_cause": "<concise root cause, 1-2 sentences>",
      "category": "<one of: assertion_error | http_error | fixture_error | timeout | import_error | other>",
      "fix_suggestion": "<concrete actionable fix, 1-3 sentences>",
      "severity": "<high | medium | low>"
    }}
  ],
  "patterns": [
    "<pattern 1 observed across multiple failures>",
    "<pattern 2 ...>"
  ],
  "recommendations": [
    "<actionable recommendation 1 for the test suite or SUT>",
    "<actionable recommendation 2 ...>"
  ]
}}

Rules:
- Output ONLY the raw JSON object, no markdown, no commentary outside JSON.
- root_cause must explain WHY the test failed (expected vs actual, missing setup, wrong assumption).
- fix_suggestion must be specific — reference the test name, endpoint, or field involved.
- patterns should identify themes across multiple failures (e.g. "All auth tests fail due to missing token").
- If there are no patterns (all failures are unrelated), return an empty array.
- severity: high = blocks core flow, medium = edge case, low = cosmetic/minor.
"""

    print("\n[failure_analyzer] Sending failures to Claude for analysis...\n")
    result_parts = []
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            result_parts.append(text)

    print()
    raw = "".join(result_parts).strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)


# ---------------------------------------------------------------------------
# Step 4 – print human-readable report
# ---------------------------------------------------------------------------

def print_report(analysis: dict) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print("  AI FAILURE ANALYSIS REPORT")
    print(sep)
    print(f"\nSUMMARY\n  {analysis['summary']}")
    print(f"\nFAILURES ANALYSED: {analysis['failure_count']}")

    if analysis.get("analyses"):
        print(f"\n{'─'*70}")
        print("  PER-TEST ANALYSIS")
        print(f"{'─'*70}")
        for a in analysis["analyses"]:
            sev_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(a["severity"], "⚪")
            print(f"\n  {sev_icon} [{a['severity'].upper()}] {a['test']}")
            print(f"     Category    : {a['category']}")
            print(f"     Root cause  : {a['root_cause']}")
            print(f"     Fix         : {a['fix_suggestion']}")

    if analysis.get("patterns"):
        print(f"\n{'─'*70}")
        print("  PATTERNS DETECTED")
        print(f"{'─'*70}")
        for i, p in enumerate(analysis["patterns"], 1):
            print(f"  {i}. {p}")

    if analysis.get("recommendations"):
        print(f"\n{'─'*70}")
        print("  RECOMMENDATIONS")
        print(f"{'─'*70}")
        for i, r in enumerate(analysis["recommendations"], 1):
            print(f"  {i}. {r}")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", "-s",
        default=DEFAULT_SUITE,
        help="Path to the pytest suite to run (file or directory)",
    )
    parser.add_argument(
        "--report-only",
        metavar="REPORT_JSON",
        help="Skip running pytest; analyse an existing pytest-json-report file",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save the analysis JSON to this filename inside generated/",
    )
    parser.add_argument(
        "--alluredir",
        help="Directory to write Allure result files (passed to pytest)",
    )
    args = parser.parse_args()

    os.makedirs(GENERATED_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # --- collect failures ---
    if args.report_only:
        print(f"[failure_analyzer] Loading existing report: {args.report_only}")
        with open(args.report_only) as f:
            report = json.load(f)
    else:
        report = run_pytest(args.suite, allure_dir=args.alluredir)

    summary = report.get("summary", {})
    failures = extract_failures(report)

    print(f"\n[failure_analyzer] Found {len(failures)} failure(s) out of "
          f"{summary.get('total', '?')} tests.")

    # --- analyse ---
    analysis = analyze_failures(failures, summary)

    # --- pretty print ---
    print_report(analysis)

    # --- save ---
    filename = args.output or "failure_analysis.json"
    out_file = os.path.join(REPORTS_DIR, filename)
    with open(out_file, "w") as f:
        json.dump(analysis, f, indent=2)
    print(f"[failure_analyzer] Analysis saved to {out_file}")


if __name__ == "__main__":
    main()
