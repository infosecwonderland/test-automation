from jsonschema import validate
from jsonschema import ValidationError
from pprint import pprint
import jwt

from schemas.auth_login import AUTH_LOGIN_ERROR_SCHEMA, AUTH_LOGIN_SUCCESS_SCHEMA


JWT_SECRET = "sut-secret"  # must match SUT auth service
JWT_ALGORITHM = "HS256"


def test_auth_login_success_schema(client, valid_credentials):
  resp, duration = client.login(
    email=valid_credentials["email"],
    password=valid_credentials["password"],
  )

  assert resp.status_code == 200
  assert duration < 0.5  # performance threshold: 500 ms

  body = resp.json()
  validate(instance=body, schema=AUTH_LOGIN_SUCCESS_SCHEMA)


def test_auth_login_invalid_credentials(client):
  resp, duration = client.login(email="wrong@example.com", password="wrongpass123")

  assert resp.status_code == 401
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=AUTH_LOGIN_ERROR_SCHEMA)
  assert body["message"] == "invalid credentials"


def test_auth_login_jwt_contents(client, valid_credentials):
  resp, duration = client.login(**valid_credentials)
  print("Status:", resp.status_code, "Duration:", duration)

  assert resp.status_code == 200

  body = resp.json()
  pprint(body)

  # Schema + basic format check
  try:
    validate(instance=body, schema=AUTH_LOGIN_SUCCESS_SCHEMA)
  except ValidationError as e:
    print("Schema validation error:", e)
    raise

  token = body["accessToken"]

  # Decode and verify JWT claims
  payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
  assert payload["sub"] == "1"

  assert payload["email"] == valid_credentials["email"]
  assert "exp" in payload

