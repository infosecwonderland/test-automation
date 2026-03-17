import pytest
import requests

from auth_utils import BASE_URL, login


SQLI_PAYLOADS = [
  "1 OR 1=1",
  "1' OR '1'='1",
  "' OR ''='",
  "1; SHUTDOWN;--",
  "1' AND '1'='1",
  "1' AND SLEEP(5)--",
  "\" OR \"\"=\"",
  "1; SELECT * FROM users;--",
  "1) OR (1=1",
  "1' UNION SELECT NULL--",
  "1' UNION SELECT 1,2,3--",
  "1' OR 'x'='x' --",
  "1 OR 1=1--",
  "1' OR 1=1#",
]


@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_sql_injection_in_login_email(payload: str):
  """
  SQL injection attempts in login email field should NOT authenticate
  and should not cause a server error.
  """
  malicious_email = f"test@example.com{payload}"

  resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": malicious_email, "password": "password123"},
  )

  # Log method, path and status code
  print(
    f"[SQLI] POST /auth/login with email='{malicious_email}' "
    f"-> {resp.status_code}"
  )

  # Expect rejection, not success or 5xx
  assert resp.status_code in (400, 401), (
    "SQLI: Login with injection-like email unexpectedly succeeded "
    f"or returned unexpected status {resp.status_code}"
  )


@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_sql_injection_in_cart_product_id(payload: str):
  """
  SQL injection attempts in productId should NOT be interpreted as valid ID
  and should not cause a server error.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  malicious_product_id = f"1{payload}"

  resp = requests.post(
    f"{BASE_URL}/cart/add",
    headers=headers,
    json={"productId": malicious_product_id, "quantity": 1},
  )

  # Log method, path and status code
  print(
    f"[SQLI] POST /cart/add with productId='{malicious_product_id}' "
    f"-> {resp.status_code}"
  )

  # Expect validation error, not success or 5xx
  assert resp.status_code in (400, 422), (
    "SQLI: cart/add accepted injection-like productId or returned unexpected status "
    f"{resp.status_code}"
  )


@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_sql_injection_in_order_id_path(payload: str):
  """
  SQL injection attempts in orderId path parameter should NOT leak data
  and should not cause a server error.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  malicious_order_id = f"1{payload}"

  resp = requests.get(
    f"{BASE_URL}/order/{malicious_order_id}",
    headers=headers,
  )

  # Log method, path and status code
  print(
    f"[SQLI] GET /order/{malicious_order_id} "
    f"-> {resp.status_code}"
  )

  # Expect 404/400, not 200 or 5xx
  assert resp.status_code in (400, 404), (
    "SQLI: order lookup with injection-like ID unexpectedly succeeded "
    f"or returned unexpected status {resp.status_code}"
  )

