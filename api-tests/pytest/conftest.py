from typing import Generator

import pytest

from client import ApiClient


@pytest.fixture(scope="session")
def base_url() -> str:
  # Points to the local SUT started in Part 1
  return "http://localhost:3000"


@pytest.fixture(scope="session")
def client(base_url: str) -> Generator[ApiClient, None, None]:
  api_client = ApiClient(base_url=base_url)
  yield api_client


@pytest.fixture(scope="session")
def valid_credentials() -> dict:
  # Matches the SUT's default seeded user
  return {"email": "test@example.com", "password": "password123"}


@pytest.fixture(scope="session")
def auth_client(client: ApiClient, valid_credentials: dict) -> Generator[ApiClient, None, None]:
  # Log in once and attach JWT for authenticated API calls
  resp, _ = client.login(
    email=valid_credentials["email"],
    password=valid_credentials["password"],
  )
  assert resp.status_code == 200
  token = resp.json()["accessToken"]
  client.session.headers.update({"Authorization": f"Bearer {token}"})
  yield client

