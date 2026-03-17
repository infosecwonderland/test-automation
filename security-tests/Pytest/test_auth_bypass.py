import requests

from auth_utils import BASE_URL


def _assert_requires_auth(method: str, path: str, json_body=None):
  url = f"{BASE_URL}{path}"
  resp = requests.request(method=method, url=url, json=json_body)
  print(f"[AUTH-BYPASS] {method} {path} -> {resp.status_code}, body={resp.text}")
  assert resp.status_code in (401, 403), (
    f"AUTH BYPASS: {method} {path} is callable without auth (got {resp.status_code})"
  )


def test_order_create_requires_auth():
  """
  Authorization bypass: creating an order without authentication
  should not be allowed.
  """
  _assert_requires_auth("POST", "/order/create", json_body={})


def test_cart_add_requires_auth():
  """
  Authorization bypass: adding to cart without authentication
  should not be allowed.
  """
  _assert_requires_auth("POST", "/cart/add", json_body={"productId": 1, "quantity": 1})


def test_cart_items_requires_auth():
  """
  Authorization bypass: fetching cart items without authentication
  should not be allowed.
  """
  _assert_requires_auth("GET", "/cart/items")


def test_cart_remove_requires_auth():
  """
  Authorization bypass: removing items from cart without authentication
  should not be allowed.
  """
  _assert_requires_auth("POST", "/cart/remove", json_body={"productId": 1})


def test_cart_clear_requires_auth():
  """
  Authorization bypass: clearing cart without authentication
  should not be allowed.
  """
  _assert_requires_auth("POST", "/cart/clear", json_body={})


def test_payment_charge_requires_auth():
  """
  Authorization bypass: charging payment without authentication
  should not be allowed.
  """
  _assert_requires_auth("POST", "/payment/charge", json_body={"orderId": "dummy", "cardNumber": "4111"})
