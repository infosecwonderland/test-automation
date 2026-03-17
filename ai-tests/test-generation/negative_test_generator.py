"""
negative_test_generator.py
--------------------------
Uses contract_loader to extract endpoint schemas from gateway.yaml,
then asks Claude to generate focused negative/edge-case pytest tests,
then runs them with pytest.

Usage:
    python ai-tests/test-generation/negative_test_generator.py
    python ai-tests/test-generation/negative_test_generator.py --output my_neg_tests.py
    python ai-tests/test-generation/negative_test_generator.py --no-run
"""

import argparse
import json
import os
import subprocess
import sys

import anthropic

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.contract_loader import (
    _body_schema,
    _is_auth_required,
    _load,
    _operations,
    _resolve_path,
    _schema_to_dict,
)

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")


def build_endpoint_summary() -> list[dict]:
    api = _load()
    endpoints = []
    for path, method, operation in _operations(api):
        resolved_path = _resolve_path(path, operation)
        body_schema = _body_schema(operation)
        endpoints.append({
            "method": method,
            "path": resolved_path,
            "auth_required": _is_auth_required(operation),
            "request_schema": _schema_to_dict(body_schema) if body_schema else None,
            "summary": operation.summary or "",
        })
    return endpoints


def load_test_data() -> dict:
    """Load generated test data from test_data.json if it exists."""
    path = os.path.join(GENERATED_DIR, "test_data.json")
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def generate_negative_tests(endpoints: list[dict]) -> str:
    client = anthropic.Anthropic()

    test_data = load_test_data()
    test_data_section = ""
    if test_data:
        test_data_section = f"""
Pre-generated test data (use these exact payloads — do NOT invent new ones):
- Invalid users: {json.dumps(test_data.get("invalid_users", []), indent=2)}
- Invalid cart items: {json.dumps(test_data.get("invalid_cart_items", []), indent=2)}
- Invalid payment cards: {json.dumps(test_data.get("invalid_payment_cards", []), indent=2)}
- Injection payloads: {json.dumps(test_data.get("injection_payloads", {}), indent=2)}
"""

    prompt = f"""You are a senior security and quality test automation engineer.
{test_data_section}
Generate exactly 25 pytest negative/edge-case test functions (no more, no less) for the API endpoints below.
Spread coverage across different endpoints and categories. Complete all 25 tests — do not truncate.

Focus exclusively on:
1. Missing required fields (one field omitted at a time)
2. Wrong data types (string where int expected, null values, empty string "")
3. Boundary values (quantity=0, quantity=-1, very long strings 1000+ chars)
4. Injection payloads in string fields: SQL injection, XSS, path traversal
   e.g. email="' OR '1'='1", name="<script>alert(1)</script>", path="../../etc/passwd"
5. Malformed JSON-like strings in place of objects
6. Extra unexpected fields (should be ignored, not cause 500)
7. Wrong HTTP method on an endpoint (e.g. GET where POST expected)

Rules:
- Use the `auth_client` fixture for auth_required=true endpoints, `client` for others.
- `auth_client` and `client` are SEPARATE independent fixtures. Never use auth_client for
  unauthorized tests — use client for those.
- `_request(method, path, json=body)` returns a TUPLE: `(response, duration)`. Always unpack:
    resp, duration = auth_client._request("POST", "/cart/add", json=body)
- For missing/invalid field tests, the OpenAPI validator may return HTML (not JSON) for 400.
  Do NOT call resp.json() for those — only assert on resp.status_code.
- For injection tests: assert resp.status_code in (400, 422) and that the server did NOT crash
  (i.e. status_code != 500). Do not assert specific error messages.
- For unexpected extra fields: assert resp.status_code in (200, 201, 400) — server must not 500.
- For wrong HTTP method tests: assert resp.status_code in (404, 405).
- Assert duration < 2.0 on every test.
- Add a one-line docstring per test describing the negative case.
- Put this import block at the top:

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-tests", "pytest"))
import pytest

SUT behaviour facts:
- Status values are uppercase: "CREATED", "PAID".
- The SUT rejects charging an already-paid order with 400.
- Boundary: quantity <= 0 returns 400. productId that doesn't exist returns 400.
- cardNumber with fewer than 4 characters returns 400.
- The SUT has NO maximum length validation on email or password — very long strings (1000+ chars)
  are accepted and return 201/200. Do NOT write tests that expect 400/422 for long email/password.
- The SUT accepts injection payloads (XSS, SQL injection, path traversal) in password fields —
  they are stored as-is. Do NOT assert 400/422 for injection strings in the password field.
  Injection tests on password should assert status_code in (200, 201) and != 500.
- The SUT accepts extra/unexpected fields in ALL request bodies without error.
  For extra-fields tests assert resp.status_code in (200, 201), NOT in (400, 422).
- For /payment/charge: orderId is looked up first. If orderId is an injection string, empty string,
  or any value that doesn't match a real orderId, the response is 404 (order not found),
  NOT 400. Assert resp.status_code in (400, 404) for invalid orderId tests.
- Card number validation is length < 4 only. Any cardNumber string with 4 or more characters
  is accepted as valid. Very long card numbers (1000+ chars) return 200 if the order exists.
  Do NOT write a test expecting 400 for a very long card number.
- Password minimum length is 8 characters. A password of exactly 8 chars IS valid (returns 201).
  Do NOT write a test expecting 400 for an 8-character password.
- For injection tests on string fields other than password (e.g. email, productId, cardNumber,
  orderId): assert resp.status_code in (400, 404, 422) and != 500. Never assert == 400 alone.

Endpoints (as JSON):
{json.dumps(endpoints, indent=2)}

Output only the Python file content, no markdown code fences."""

    result_parts = []
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            result_parts.append(text)

    print()
    return "".join(result_parts)


def run_tests(test_file: str) -> None:
    print(f"\n[negative_test_generator] Running tests with pytest...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", help="Output filename inside generated/")
    parser.add_argument("--no-run", action="store_true")
    args = parser.parse_args()

    os.makedirs(GENERATED_DIR, exist_ok=True)

    print("[negative_test_generator] Extracting endpoints via contract_loader...")
    endpoints = build_endpoint_summary()
    print(f"[negative_test_generator] Found {len(endpoints)} endpoints. Sending to Claude...\n")

    code = generate_negative_tests(endpoints)

    filename = args.output or "test_negative_cases.py"
    test_file = os.path.join(GENERATED_DIR, filename)
    with open(test_file, "w") as fh:
        fh.write(code)
    print(f"\n[negative_test_generator] Written to {test_file}")

    if not args.no_run:
        run_tests(test_file)


if __name__ == "__main__":
    main()
