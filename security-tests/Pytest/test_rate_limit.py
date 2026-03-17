import collections
import time

import allure
import pytest
import requests

from auth_utils import BASE_URL, login
from utils.contract_loader import rate_limited_endpoints

_BURST_SIZE = 30
_BURST_DELAY = 0.02


def _burst(method, path, *, headers=None, body=None):
    url = BASE_URL + path
    statuses = []
    for _ in range(_BURST_SIZE):
        resp = requests.request(method=method, url=url, headers=headers, json=body)
        statuses.append(resp.status_code)
        time.sleep(_BURST_DELAY)
    counter = collections.Counter(statuses)
    print(f"[RATE-LIMIT] {method} {path} statuses: {dict(counter)}")
    return counter


@allure.feature("Security")
@allure.story("Rate Limiting")
@pytest.mark.parametrize(
    "endpoint",
    rate_limited_endpoints(),
    ids=lambda e: f"{e['method']} {e['path']}",
)
def test_rate_limit(endpoint):
    """
    Endpoints tagged x-rate-limited in the OpenAPI contract must return
    429 when burst-requested beyond their threshold.
    """
    headers = {}
    if endpoint["auth_required"]:
        headers["Authorization"] = f"Bearer {login()}"

    counter = _burst(
        endpoint["method"],
        endpoint["path"],
        headers=headers or None,
        body=endpoint["body"],
    )

    assert 429 in counter, (
        f"RATE LIMITING MISSING on {endpoint['method']} {endpoint['path']}: "
        f"no 429 seen in {_BURST_SIZE} requests — got {dict(counter)}"
    )
