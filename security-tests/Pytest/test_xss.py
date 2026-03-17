import allure
import pytest
import requests

from auth_utils import BASE_URL, login
from utils.contract_loader import injectable_endpoints

XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert`xss`>",
    "\"><script>alert('xss')</script>",
    "<body onload=alert('xss')>",
]

_PARAMS = [
    (ep, payload)
    for ep in injectable_endpoints()
    for payload in XSS_PAYLOADS
]


@allure.feature("Security")
@allure.story("XSS")
@pytest.mark.parametrize(
    "endpoint,payload",
    _PARAMS,
    ids=lambda x: f"{x['method']} {x['path']} [{x['field']}]" if isinstance(x, dict) else x,
)
def test_xss(endpoint, payload):
    """
    XSS payloads in string request-body fields must not be reflected
    unescaped in the response and must not cause a server error (5xx).
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
        f"[XSS] {endpoint['method']} {endpoint['path']} "
        f"field={endpoint['field']} payload={payload!r} -> {resp.status_code}"
    )

    assert resp.status_code < 500, (
        f"XSS payload caused server error on {endpoint['method']} {endpoint['path']}: "
        f"{resp.status_code}"
    )
    assert payload not in resp.text, (
        f"Potential reflected XSS: payload appears unescaped in response from "
        f"{endpoint['method']} {endpoint['path']} field={endpoint['field']!r}"
    )
