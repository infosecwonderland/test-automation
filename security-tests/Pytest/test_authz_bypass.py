import time

import requests

from auth_utils import BASE_URL, login


def _create_order_for_default_user() -> str:
  """
  Create an order as the default seeded user (test@example.com)
  and return the orderId.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  # Ensure there is at least one item in the cart
  resp_add = requests.post(
    f"{BASE_URL}/cart/add",
    headers=headers,
    json={"productId": 1, "quantity": 1},
  )
  assert resp_add.status_code == 201, f"failed to add to cart: {resp_add.status_code} {resp_add.text}"

  resp_order = requests.post(
    f"{BASE_URL}/order/create",
    headers=headers,
    json={},
  )
  assert resp_order.status_code == 201, f"failed to create order: {resp_order.status_code} {resp_order.text}"
  body = resp_order.json()
  return body["orderId"]


def _register_and_login_new_user() -> str:
  """
  Register a second user and return its JWT access token.
  """
  unique_suffix = int(time.time() * 1000)
  email = f"other-{unique_suffix}@example.com"
  password = "password123"

  resp_reg = requests.post(
    f"{BASE_URL}/auth/register",
    json={"email": email, "password": password},
  )
  assert resp_reg.status_code == 201, f"failed to register second user: {resp_reg.status_code} {resp_reg.text}"

  # Reuse the login helper with explicit credentials
  token = login(email=email, password=password)
  return token


def test_authorization_bypass_order_leak_between_users():
  """
  Authorization bypass: User B must not be able to see
  orders that belong to User A.

  Today, GET /order/:orderId does not enforce user ownership
  or authentication at all, so this test will currently fail,
  highlighting an access-control vulnerability.
  """
  # Arrange: create an order as default user (User A)
  order_id = _create_order_for_default_user()

  # Act: authenticate as a different user (User B)
  user_b_token = _register_and_login_new_user()
  headers_b = {"Authorization": f"Bearer {user_b_token}"}

  # Attempt to access User A's order as User B
  resp = requests.get(f"{BASE_URL}/order/{order_id}", headers=headers_b)

  print(
    f"[AUTHZ-BYPASS] GET /order/{order_id} as User B -> "
    f"{resp.status_code}, body={resp.text}"
  )

  # Security expectation: either 403 (forbidden) or 404 (not found).
  assert resp.status_code in (403, 404), (
    "AUTHORIZATION BYPASS: User B can access User A's order "
    f"via GET /order/{order_id} (got {resp.status_code})"
  )

