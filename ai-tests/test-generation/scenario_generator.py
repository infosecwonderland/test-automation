"""
scenario_generator.py
---------------------
Uses contract_loader to extract endpoint info from gateway.yaml,
then asks Claude to generate pytest test scenarios from that data,
then runs the generated tests with pytest.

Usage:
    python ai-tests/test-generation/scenario_generator.py
    python ai-tests/test-generation/scenario_generator.py --output generated_scenarios.py
    python ai-tests/test-generation/scenario_generator.py --no-run
"""

import argparse
import json
import os
import subprocess
import sys

import anthropic

# make utils.contract_loader importable from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.contract_loader import (
    _body_schema,
    _is_auth_required,
    _load,
    _operations,
    _resolve_path,
    _schema_to_dict,
    response_schema,
)


def _anthropic_client() -> anthropic.Anthropic:
    """
    Build an Anthropic client with explicit auth checks so failures are actionable.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")
    if not api_key and not auth_token:
        raise RuntimeError(
            "Missing Anthropic credentials. Set ANTHROPIC_API_KEY (recommended) "
            "or ANTHROPIC_AUTH_TOKEN before running scenario generation.\n"
            "Example (zsh): export ANTHROPIC_API_KEY='your-key'"
        )
    return anthropic.Anthropic(api_key=api_key, auth_token=auth_token)


def build_endpoint_summary() -> list[dict]:
    """Use contract_loader to extract structured endpoint info."""
    api = _load()
    endpoints = []

    for path, method, operation in _operations(api):
        resolved_path = _resolve_path(path, operation)
        body_schema = _body_schema(operation)

        # collect response schemas for all defined status codes
        responses = {}
        for status_code in operation.responses or {}:
            try:
                schema = response_schema(path, method, int(status_code))
                if schema:
                    responses[status_code] = schema
            except (KeyError, ValueError):
                pass

        endpoints.append({
            "method": method,
            "path": resolved_path,
            "auth_required": _is_auth_required(operation),
            "request_schema": _schema_to_dict(body_schema) if body_schema else None,
            "response_schemas": responses,
            "summary": operation.summary or "",
        })

    return endpoints


def load_test_data() -> dict:
    """Load generated test data from test_data.json if it exists."""
    path = os.path.join(os.path.dirname(__file__), "generated", "test_data.json")
    if os.path.isfile(path):
        with open(path) as f:
            return json.load(f)
    return {}


def generate_scenarios(endpoints: list[dict]) -> str:
    client = _anthropic_client()

    test_data = load_test_data()
    test_data_section = ""
    if test_data:
        test_data_section = f"""
Pre-generated test data (use these exact values in your tests — do NOT invent new ones):
- Valid users (pick any for registration/login): {json.dumps(test_data.get("users", [])[:3], indent=2)}
- Valid cart items (use these productId/quantity pairs): {json.dumps(test_data.get("cart_items", []), indent=2)}
- Valid payment cards (use these card numbers): {json.dumps(test_data.get("payment_cards", [])[:3], indent=2)}
- Order scenarios (items to add before creating an order): {json.dumps(test_data.get("order_scenarios", [])[:2], indent=2)}
"""

    prompt = f"""You are a senior test automation engineer.

Generate exactly 25 pytest test functions (no more, no less) for the API endpoints below.
Spread coverage across different endpoints. Complete all 25 tests — do not truncate.
{test_data_section}
Rules:
- Use the `auth_client` fixture for endpoints where auth_required=true, `client` for others.
- `_request(method, path, json=body)` returns a TUPLE: `(response, duration)`. Always unpack like:
    resp, duration = auth_client._request("POST", "/cart/add", json=body)
- Assert `resp.status_code == <expected>` and `duration < 2.0`.
- Add a one-line docstring per test.
- Put this import block at the top of the file:

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-tests", "pytest"))
import pytest

CRITICAL fixture rules:
- `client` and `auth_client` are SEPARATE session-scoped fixtures with independent HTTP sessions.
  `auth_client` already has the Authorization header set; `client` never does.
- For unauthorized tests (testing that missing auth returns 401), ALWAYS use the `client` fixture.
  Never use `auth_client` for unauthorized tests.

CRITICAL response body rules:
- When testing missing/invalid required fields (e.g. missing productId, missing quantity, missing
  cardNumber), the OpenAPI request validator may return a 400 with an HTML error page, not JSON.
  For these validation-error tests, do NOT call `resp.json()` — only assert on `resp.status_code`.
- Only call `resp.json()` and assert on body fields when testing happy-path responses or errors
  where the SUT logic itself returns JSON (e.g. 404 "Order not found", 400 "Cart is empty").

CRITICAL path parameter rules:
- For "resource not found" tests using path parameters (e.g. GET /order/{{orderId}}), use a
  realistic-looking but nonexistent numeric ID like "000000000000" rather than strings like
  "nonexistent-id-000", because the OpenAPI validator may reject non-numeric path params with 400.
  Assert `resp.status_code in (400, 404)` to tolerate both validator and handler responses.

CRITICAL SUT behaviour rules:
- The SUT rejects charging an already-paid order with 400 "Order already paid".
  It is correct to write a test that charges an order twice and expects 400 on the second attempt.
- Order and payment status values are uppercase strings: "CREATED", "PAID". Use uppercase in assertions.

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


GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")


def run_tests(test_file: str) -> None:
    """Run the generated test file with pytest."""
    print(f"\n[scenario_generator] Running generated tests with pytest...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", help="Output filename inside ai-tests/test-generation/generated/")
    parser.add_argument("--no-run", action="store_true", help="Generate only, do not run pytest")
    args = parser.parse_args()

    os.makedirs(GENERATED_DIR, exist_ok=True)

    print("[scenario_generator] Extracting endpoints via contract_loader...")
    endpoints = build_endpoint_summary()
    print(f"[scenario_generator] Found {len(endpoints)} endpoints. Sending to Claude...\n")

    try:
        code = generate_scenarios(endpoints)
    except RuntimeError as exc:
        print(f"[scenario_generator] {exc}")
        sys.exit(2)

    filename = args.output or "test_ai_scenarios.py"
    test_file = os.path.join(GENERATED_DIR, filename)
    with open(test_file, "w") as fh:
        fh.write(code)
    print(f"\n[scenario_generator] Written to {test_file}")

    if not args.no_run:
        run_tests(test_file)


if __name__ == "__main__":
    main()
