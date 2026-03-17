"""
Fixture bridge for AI-generated tests.
Starts the SUT and provides client / auth_client fixtures,
mirroring api-tests/pytest/conftest.py.
"""
import os
import subprocess
import sys
import time

import pytest
import requests

# make api-tests/pytest importable (for client.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api-tests", "pytest"))

from client import ApiClient

BASE_URL = os.getenv("SUT_BASE_URL", "http://localhost:3000")
SUT_INDEX = os.path.join(os.path.dirname(__file__), "..", "..", "sut", "index.js")


def _sut_is_up(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=2).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def sut_server():
    already_running = _sut_is_up(BASE_URL)
    proc = None
    if not already_running:
        proc = subprocess.Popen(["node", SUT_INDEX], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(30):
            if _sut_is_up(BASE_URL):
                break
            time.sleep(1)
        else:
            proc.terminate()
            pytest.exit("SUT did not start in time", returncode=1)
    yield
    if proc:
        proc.terminate()
        proc.wait()


@pytest.fixture(scope="session")
def client():
    # Unauthenticated client — never set auth headers on this object
    return ApiClient(base_url=BASE_URL)


@pytest.fixture(scope="session")
def auth_client():
    # Separate instance so auth headers never pollute the plain `client` fixture
    ac = ApiClient(base_url=BASE_URL)
    email = os.getenv("SUT_TEST_EMAIL", "test@example.com")
    password = os.getenv("SUT_TEST_PASSWORD", "password123")
    ac._request("POST", "/auth/register", json={"email": email, "password": password})
    resp, _ = ac.login(email=email, password=password)
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    ac.session.headers.update({"Authorization": f"Bearer {resp.json()['accessToken']}"})
    return ac


@pytest.fixture(autouse=True)
def _allure_suite_labels():
    import allure
    allure.dynamic.parent_suite("AI Tests")
    allure.dynamic.suite("Generated Tests")
