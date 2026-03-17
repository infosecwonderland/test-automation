import allure

from jsonschema import validate

from utils.contract_loader import response_schema


@allure.feature("API Tests")
@allure.story("Products")
def test_get_products_success(client):
    resp, duration = client.get_products()

    assert resp.status_code == 200
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/products", "GET", 200))
    assert len(body) >= 1
