import jwt
from jsonschema import validate

from utils.contract_loader import response_schema

JWT_ALGORITHM = "HS256"


def test_auth_login_success(client, valid_credentials):
    resp, duration = client.login(**valid_credentials)

    assert resp.status_code == 200
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/auth/login", "POST", 200))


def test_auth_login_invalid_credentials(client):
    resp, duration = client.login(email="wrong@example.com", password="wrongpass123")

    assert resp.status_code == 401
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/auth/login", "POST", 401))
    assert body["message"] == "invalid credentials"


def test_auth_login_jwt_contents(client, valid_credentials):
    resp, _ = client.login(**valid_credentials)
    assert resp.status_code == 200

    token = resp.json()["accessToken"]
    payload = jwt.decode(token, options={"verify_signature": False}, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "1"
    assert payload["email"] == valid_credentials["email"]
    assert "exp" in payload
