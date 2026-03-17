"""
data_generator.py
-----------------
Uses Claude to generate realistic synthetic test data for the e-commerce SUT.

Generates:
  - users      : valid registration credentials (email + password)
  - products   : product search queries and expected product names
  - cart_items : valid (productId, quantity) pairs and invalid boundary cases
  - orders     : order scenarios (items list + expected total)
  - payments   : valid and invalid card number samples

Output is written to:
  ai-tests/test-generation/generated/test_data.json

Usage:
    python ai-tests/test-generation/data_generator.py
    python ai-tests/test-generation/data_generator.py --no-run
    python ai-tests/test-generation/data_generator.py --output my_data.json
"""

import argparse
import json
import os
import subprocess
import sys

import anthropic

GENERATED_DIR = os.path.join(os.path.dirname(__file__), "generated")

# SUT product catalogue (matches sut/index.js in-memory products)
KNOWN_PRODUCTS = [
    {"id": 1, "name": "Laptop",     "price": 1200},
    {"id": 2, "name": "Headphones", "price": 200},
    {"id": 3, "name": "Phone",      "price": 800},
]


def generate_test_data() -> dict:
    client = anthropic.Anthropic()

    prompt = f"""You are a senior QA data engineer for an e-commerce platform.

Generate synthetic test data for automated tests against this SUT:

Products in the catalogue (fixed, cannot be changed):
{json.dumps(KNOWN_PRODUCTS, indent=2)}

SUT rules:
- Email must be a valid email format (contains @).
- Password minimum length is 8 characters.
- productId must be 1, 2, or 3 (only valid IDs in the SUT).
- quantity must be a positive integer >= 1.
- cardNumber must be at least 4 characters long to be valid.
- Order status values: "CREATED", "PAID" (uppercase).

Generate a JSON object with exactly these keys and structures:

{{
  "users": [
    // 10 valid user objects, each with unique email and valid password (8+ chars)
    // Format: {{"email": "...", "password": "..."}}
  ],
  "invalid_users": [
    // 5 invalid user objects for negative testing
    // Each has a "scenario" key explaining why it's invalid, plus "email" and/or "password"
    // Scenarios: missing_email, missing_password, short_password (7 chars), empty_email, null_password
    // Format: {{"scenario": "...", "email": "...", "password": "..."}}
  ],
  "cart_items": [
    // 6 valid cart item objects
    // Format: {{"productId": <int 1-3>, "quantity": <int 1-10>}}
  ],
  "invalid_cart_items": [
    // 5 invalid cart item objects for negative testing
    // Each has a "scenario" key
    // Scenarios: zero_quantity, negative_quantity, nonexistent_product (id=999), missing_quantity, missing_product_id
    // Format: {{"scenario": "...", "productId": <int or null>, "quantity": <int or null>}}
  ],
  "payment_cards": [
    // 5 valid card number strings (4+ chars, realistic-looking)
    // Format: {{"card_number": "...", "description": "..."}}
  ],
  "invalid_payment_cards": [
    // 3 invalid card number strings (fewer than 4 chars)
    // Format: {{"card_number": "...", "description": "..."}}
  ],
  "order_scenarios": [
    // 4 order scenarios, each describing items to add to cart before creating an order
    // Format: {{
    //   "description": "...",
    //   "items": [{{"productId": <int>, "quantity": <int>}}],
    //   "expected_total": <number>
    // }}
  ],
  "injection_payloads": {{
    "sql": ["...", "...", "..."],       // 3 SQL injection strings
    "xss": ["...", "...", "..."],       // 3 XSS payload strings
    "path_traversal": ["...", "..."]   // 2 path traversal strings
  }}
}}

Rules for your output:
- Output ONLY the raw JSON object, no markdown fences, no commentary.
- All emails must be unique across users and invalid_users.
- Make the data realistic and varied (different names, domains, quantities, card formats).
- For order_scenarios, expected_total must be the correct sum: sum(product.price * quantity).
  Laptop=1200, Headphones=200, Phone=800.
"""

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

    # Strip markdown fences if Claude added them despite instruction
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)


def run_smoke_tests(data_file: str) -> None:
    """Run a quick pytest smoke-test that validates the generated data file."""
    test_file = os.path.join(GENERATED_DIR, "test_data_smoke.py")
    smoke = f'''"""
Auto-generated smoke tests that validate the structure of test_data.json.
"""
import json
import os
import pytest

DATA_FILE = os.path.join(os.path.dirname(__file__), "test_data.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_FILE) as f:
        return json.load(f)


def test_data_file_exists():
    """test_data.json must exist."""
    assert os.path.isfile(DATA_FILE)


def test_users_count(data):
    """Must have at least 5 valid users."""
    assert len(data["users"]) >= 5


def test_users_have_required_fields(data):
    """Each user must have email and password."""
    for u in data["users"]:
        assert "email" in u and "@" in u["email"]
        assert "password" in u and len(u["password"]) >= 8


def test_invalid_users_have_scenarios(data):
    """Each invalid user must have a scenario key."""
    for u in data["invalid_users"]:
        assert "scenario" in u


def test_cart_items_valid(data):
    """Valid cart items must have productId in 1-3 and quantity >= 1."""
    for item in data["cart_items"]:
        assert item["productId"] in (1, 2, 3)
        assert item["quantity"] >= 1


def test_invalid_cart_items_have_scenarios(data):
    """Each invalid cart item must have a scenario key."""
    for item in data["invalid_cart_items"]:
        assert "scenario" in item


def test_payment_cards_valid(data):
    """Valid cards must be 4+ chars."""
    for card in data["payment_cards"]:
        assert len(card["card_number"]) >= 4


def test_payment_cards_invalid(data):
    """Invalid cards must be fewer than 4 chars."""
    for card in data["invalid_payment_cards"]:
        assert len(card["card_number"]) < 4


def test_order_scenarios_totals(data):
    """Order scenario expected_total must match product prices."""
    prices = {{1: 1200, 2: 200, 3: 800}}
    for scenario in data["order_scenarios"]:
        calc = sum(prices[i["productId"]] * i["quantity"] for i in scenario["items"])
        assert calc == scenario["expected_total"], (
            f"{{scenario['description']}}: expected {{scenario['expected_total']}} but calc={{calc}}"
        )


def test_injection_payloads_present(data):
    """Injection payloads must have sql, xss, path_traversal keys."""
    payloads = data["injection_payloads"]
    assert len(payloads["sql"]) >= 2
    assert len(payloads["xss"]) >= 2
    assert len(payloads["path_traversal"]) >= 1
'''
    with open(test_file, "w") as f:
        f.write(smoke)

    print(f"\n[data_generator] Running smoke tests against {data_file}...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", help="Output filename inside generated/")
    parser.add_argument("--no-run", action="store_true", help="Generate only, skip smoke tests")
    args = parser.parse_args()

    os.makedirs(GENERATED_DIR, exist_ok=True)

    print("[data_generator] Asking Claude to generate synthetic test data...\n")
    data = generate_test_data()

    filename = args.output or "test_data.json"
    out_file = os.path.join(GENERATED_DIR, filename)
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\n[data_generator] Written to {out_file}")

    # Summary
    print(f"\n[data_generator] Generated:")
    for key, val in data.items():
        count = len(val) if isinstance(val, (list, dict)) else val
        if isinstance(val, dict):
            count = {k: len(v) for k, v in val.items()}
        print(f"  {key}: {count}")

    if not args.no_run:
        run_smoke_tests(out_file)


if __name__ == "__main__":
    main()
