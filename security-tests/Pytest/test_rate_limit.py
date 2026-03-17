import collections
import time

import requests

from auth_utils import BASE_URL, login


def _burst_requests(method: str, path: str, *, headers=None, json_body=None, attempts: int = 30):
  url = f"{BASE_URL}{path}"
  statuses = []

  for i in range(attempts):
    body = json_body
    if callable(json_body):
      body = json_body(i)

    resp = requests.request(method=method, url=url, headers=headers, json=body)
    statuses.append(resp.status_code)
    time.sleep(0.02)

  counter = collections.Counter(statuses)
  print(f"[RATE-LIMIT] {method} {path} statuses: {dict(counter)}")
  return counter


def test_rate_limiting_on_auth_login():
  """
  Rate limiting: aggressive login attempts should eventually be throttled.
  """
  counter = _burst_requests(
    "POST",
    "/auth/login",
    json_body=lambda i: {"email": "test@example.com", "password": f"wrong-password-{i}"},
  )

  assert 429 in counter, (
    "RATE LIMITING MISSING on /auth/login: expected at least one 429 Too Many Requests "
    f"when sending burst of logins, but saw {dict(counter)}"
  )


def test_rate_limiting_on_cart_add():
  """
  Rate limiting: repeated POST /cart/add with valid auth
  should eventually be throttled.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  counter = _burst_requests(
    "POST",
    "/cart/add",
    headers=headers,
    json_body=lambda i: {"productId": 1, "quantity": 1},
  )

  assert 429 in counter, (
    "RATE LIMITING MISSING on /cart/add: expected at least one 429 Too Many Requests "
    f"when sending burst of cart additions, but saw {dict(counter)}"
  )


def test_rate_limiting_on_order_create():
  """
  Rate limiting: repeated POST /order/create with valid auth
  should eventually be throttled.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  # Seed cart once so order creation is not blocked by empty cart
  requests.post(
    f"{BASE_URL}/cart/add",
    headers=headers,
    json={"productId": 1, "quantity": 1},
  )

  counter = _burst_requests(
    "POST",
    "/order/create",
    headers=headers,
    json_body={},
  )

  assert 429 in counter, (
    "RATE LIMITING MISSING on /order/create: expected at least one 429 Too Many Requests "
    f"when sending burst of order creations, but saw {dict(counter)}"
  )


def test_rate_limiting_on_payment_charge():
  """
  Rate limiting: repeated POST /payment/charge with valid auth
  should eventually be throttled.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  # Create one valid order to charge
  requests.post(
    f"{BASE_URL}/cart/add",
    headers=headers,
    json={"productId": 1, "quantity": 1},
  )
  order_resp = requests.post(
    f"{BASE_URL}/order/create",
    headers=headers,
    json={},
  )
  order_id = order_resp.json().get("orderId", "dummy")

  counter = _burst_requests(
    "POST",
    "/payment/charge",
    headers=headers,
    json_body=lambda i: {"orderId": order_id, "cardNumber": "4111111111111111"},
  )

  assert 429 in counter, (
    "RATE LIMITING MISSING on /payment/charge: expected at least one 429 Too Many Requests "
    f"when sending burst of payment charges, but saw {dict(counter)}"
  )

