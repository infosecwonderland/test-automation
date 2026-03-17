import time
from typing import Any, Dict, Optional, Tuple

import requests


class ApiClient:
  """
  Thin wrapper around requests to centralize:
  - base URL
  - common headers
  - basic logging and timing
  """

  def __init__(self, base_url: str):
    self.base_url = base_url.rstrip("/")
    self.session = requests.Session()

  def _request(
    self,
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
  ) -> Tuple[requests.Response, float]:
    url = f"{self.base_url}{path}"
    start = time.perf_counter()
    resp = self.session.request(method=method, url=url, json=json, headers=headers)
    duration = time.perf_counter() - start
    # simple console log for debugging
    print(f"[API] {method} {url} -> {resp.status_code} in {duration*1000:.1f} ms")
    return resp, duration

  # Convenience wrappers for specific endpoints

  def login(self, email: str, password: str):
    return self._request(
      "POST",
      "/auth/login",
      json={"email": email, "password": password},
    )

  def get_products(self):
    return self._request("GET", "/products")

  def add_to_cart(self, product_id: int, quantity: int):
    return self._request(
      "POST",
      "/cart/add",
      json={"productId": product_id, "quantity": quantity},
    )

  def create_order(self):
    return self._request("POST", "/order/create", json={})

  def charge_payment(self, order_id: str, card_number: str):
    return self._request(
      "POST",
      "/payment/charge",
      json={"orderId": order_id, "cardNumber": card_number},
    )

  def clear_cart(self):
    return self._request("POST", "/cart/clear", json={})


