import html

import allure
import pytest
import requests

from auth_utils import BASE_URL, login


XSS_PAYLOADS = [
  "<script>alert('xss')</script>",
  "<img src=x onerror=alert(1)>",
  "<svg/onload=alert`xss`>",
  "\"><script>alert('xss')</script>",
  "<body onload=alert('xss')>",
]


@allure.feature("Security")
@allure.story("XSS")
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_xss_in_search_query_is_escaped(payload: str):
  """
  XSS payloads in search query parameters should not be reflected unsanitized
  in the HTML or JSON response.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  resp = requests.get(
    f"{BASE_URL}/products?search={payload}",
    headers=headers,
  )

  print(
    f"[XSS] GET /products?search={html.escape(payload)} "
    f"-> {resp.status_code}, content-type={resp.headers.get('Content-Type')}"
  )

  # Response should be OK (or at least not a server error)
  assert resp.status_code < 500, (
    f"XSS search payload caused server error: {resp.status_code}"
  )

  body_text = resp.text
  # The raw payload string should not appear unescaped in the response body
  assert payload not in body_text, (
    "Potential reflected XSS: payload appears unescaped in response body"
  )


@allure.feature("Security")
@allure.story("XSS")
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_xss_in_cart_error_message_is_sanitized(payload: str):
  """
  XSS payloads in user-controlled fields should not be echoed back
  in error messages without sanitization.
  """
  token = login()
  headers = {"Authorization": f"Bearer {token}"}

  # Use an obviously invalid product name / ID to trigger an error path
  resp = requests.post(
    f"{BASE_URL}/cart/add",
    headers=headers,
    json={"productId": payload, "quantity": 1},
  )

  print(
    f"[XSS] POST /cart/add with productId={html.escape(payload)} "
    f"-> {resp.status_code}, content-type={resp.headers.get('Content-Type')}"
  )

  # Expect a client error, not 2xx or 5xx
  assert 400 <= resp.status_code < 500, (
    f"Unexpected status for XSS payload in cart/add: {resp.status_code}"
  )

  body_text = resp.text
  assert payload not in body_text, (
    "Potential reflected XSS in cart/add error response"
  )

