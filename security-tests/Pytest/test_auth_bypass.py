import allure
import pytest
import requests

from auth_utils import BASE_URL
from utils.contract_loader import auth_required_endpoints


@allure.feature("Security")
@allure.story("Authentication Bypass")
@pytest.mark.parametrize(
    "endpoint",
    auth_required_endpoints(),
    ids=lambda e: f"{e['method']} {e['path']}",
)
def test_requires_auth(endpoint):
    """
    Every endpoint secured by bearerAuth in the OpenAPI contract must
    reject unauthenticated requests with 401 or 403.
    """
    resp = requests.request(
        method=endpoint["method"],
        url=BASE_URL + endpoint["path"],
        json=endpoint["body"],
    )
    assert resp.status_code in (401, 403), (
        f"AUTH BYPASS: {endpoint['method']} {endpoint['path']} "
        f"is callable without auth (got {resp.status_code})"
    )
