import os
import subprocess
import sys
import time
from typing import Generator

import pytest
import requests

# Make the repo root importable so utils/contract_loader is available
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from client import ApiClient

BASE_URL = os.getenv("SUT_BASE_URL", "http://localhost:3000")
SUT_INDEX = os.path.join(os.path.dirname(__file__), "../../sut/index.js")


def _sut_is_up(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def sut_server():
    """
    Start the SUT before the test session and stop it after.
    If the SUT is already running (local dev), reuse it without restarting.
    """
    already_running = _sut_is_up(BASE_URL)

    proc = None
    if not already_running:
        proc = subprocess.Popen(
            ["node", SUT_INDEX],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            if _sut_is_up(BASE_URL):
                break
            time.sleep(1)
        else:
            proc.terminate()
            pytest.exit("SUT did not start in time", returncode=1)

    yield

    if proc is not None:
        proc.terminate()
        proc.wait()


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def client(base_url: str) -> Generator[ApiClient, None, None]:
    api_client = ApiClient(base_url=base_url)
    yield api_client


@pytest.fixture(scope="session")
def valid_credentials() -> dict:
    return {
        "email": os.getenv("SUT_TEST_EMAIL", "test@example.com"),
        "password": os.getenv("SUT_TEST_PASSWORD", "password123"),
    }


@pytest.fixture(scope="session")
def auth_client(client: ApiClient, valid_credentials: dict) -> Generator[ApiClient, None, None]:
    # Register first (idempotent — 409 means already exists)
    client._request(
        "POST",
        "/auth/register",
        json={"email": valid_credentials["email"], "password": valid_credentials["password"]},
    )
    resp, _ = client.login(
        email=valid_credentials["email"],
        password=valid_credentials["password"],
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["accessToken"]
    client.session.headers.update({"Authorization": f"Bearer {token}"})
    yield client
