import base64
import json

import pytest
import requests

from auth_utils import BASE_URL, login, call_me


def _b64url_decode(segment: str) -> bytes:
  padding = '=' * (-len(segment) % 4)
  return base64.urlsafe_b64decode(segment + padding)


def _b64url_encode(data: bytes) -> str:
  return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _split_token(token: str):
  parts = token.split(".")
  assert len(parts) == 3, f"Unexpected JWT format: {token}"
  return parts


def test_jwt_payload_tamper_without_resign_is_rejected():
  """
  If the JWT payload is modified without recomputing the signature,
  /auth/me should reject it (401/403), not accept it.
  """
  token = login()
  header_b64, payload_b64, signature_b64 = _split_token(token)

  # Decode payload and flip a claim (e.g. email) without resigning
  payload = json.loads(_b64url_decode(payload_b64))
  original_email = payload.get("email", "test@example.com")
  payload["email"] = "attacker@example.com"

  tampered_payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
  tampered_token = ".".join([header_b64, tampered_payload_b64, signature_b64])

  resp = call_me(tampered_token)

  print(
    f"[JWT] Tampered payload token for email {original_email} -> "
    f"{resp.status_code}, body={resp.text[:200]}"
  )

  assert resp.status_code in (401, 403), (
    "JWT tampering: modified payload was accepted by /auth/me"
  )


def test_jwt_invalid_signature_is_rejected():
  """
  If the JWT signature is replaced with garbage, the token must be rejected.
  """
  token = login()
  header_b64, payload_b64, _signature_b64 = _split_token(token)

  invalid_sig = "invalidsignature"
  forged_token = ".".join([header_b64, payload_b64, invalid_sig])

  resp = call_me(forged_token)

  print(
    f"[JWT] Forged signature token -> {resp.status_code}, body={resp.text[:200]}"
  )

  assert resp.status_code in (401, 403), (
    "JWT tampering: token with invalid signature was accepted by /auth/me"
  )


def test_jwt_used_without_bearer_prefix_is_rejected():
  """
  Using a raw JWT without the 'Bearer ' prefix should not be accepted.
  """
  token = login()

  resp = requests.get(
    f"{BASE_URL}/auth/me",
    headers={"Authorization": token},  # missing Bearer
  )

  print(
    f"[JWT] Raw token without Bearer prefix -> {resp.status_code}, "
    f"body={resp.text[:200]}"
  )

  assert resp.status_code in (400, 401, 403), (
    "JWT tampering: raw token without 'Bearer' prefix was accepted"
  )

