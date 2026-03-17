import allure
import pytest
import requests

from auth_utils import BASE_URL, login
from utils.contract_loader import injectable_endpoints

SQLI_PAYLOADS = [
    "1 OR 1=1",
    "1' OR '1'='1",
    "' OR ''='",
    "1; SHUTDOWN;--",
    "1' AND SLEEP(5)--",
    "1' UNION SELECT NULL--",
    "1' OR 'x'='x' --",
    "1 OR 1=1--",
]

_PARAMS = [
    (ep, payload)
    for ep in injectable_endpoints()
    for payload in SQLI_PAYLOADS
]


@allure.feature("Security")
@allure.story("SQL Injection")
@pytest.mark.parametrize(
    "endpoint,payload",
    _PARAMS,
    ids=lambda x: f"{x['method']} {x['path']} [{x['field']}]" if isinstance(x, dict) else x,
)
def test_sql_injection(endpoint, payload):
    """
    SQL injection payloads in string request-body fields must not cause
    the server to succeed (2xx) or crash (5xx).  Any 4xx response is
    an acceptable rejection.
    """
    headers = {}
    if endpoint["auth_required"]:
        headers["Authorization"] = f"Bearer {login()}"

    body = {**endpoint["base_body"], endpoint["field"]: payload}

    resp = requests.request(
        method=endpoint["method"],
        url=BASE_URL + endpoint["path"],
        headers=headers or None,
        json=body,
    )

    print(
        f"[SQLI] {endpoint['method']} {endpoint['path']} "
        f"field={endpoint['field']} payload={payload!r} -> {resp.status_code}"
    )

    assert 400 <= resp.status_code < 500, (
        f"SQLI: {endpoint['method']} {endpoint['path']} field={endpoint['field']!r} "
        f"returned unexpected status {resp.status_code} for payload {payload!r}"
    )
