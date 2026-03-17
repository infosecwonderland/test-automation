import os

import requests


BASE_URL = os.getenv("SECURITY_BASE_URL", "http://localhost:3000")


def login(email: str = "test@example.com", password: str = "password123") -> str:
  """
  Helper to obtain a valid JWT from the SUT.
  Returns the raw access token string.
  """
  resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": email, "password": password},
  )
  assert resp.status_code == 200, f"login failed: {resp.status_code} {resp.text}"
  body = resp.json()
  return body["accessToken"]


def call_me(token: str):
  return requests.get(
    f"{BASE_URL}/auth/me",
    headers={"Authorization": f"Bearer {token}"},
  )

