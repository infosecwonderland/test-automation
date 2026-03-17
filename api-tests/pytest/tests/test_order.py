import allure

from jsonschema import validate

from utils.contract_loader import response_schema


@allure.feature("API Tests")
@allure.story("Order")
def test_order_create_success(auth_client):
    auth_client.clear_cart()
    add_resp, _ = auth_client.add_to_cart(product_id=1, quantity=2)
    assert add_resp.status_code == 201

    resp, duration = auth_client.create_order()

    assert resp.status_code == 201
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/order/create", "POST", 201))
    assert body["message"] == "Order created"
    assert isinstance(body["orderId"], str)
    assert body["total"] > 0


@allure.feature("API Tests")
@allure.story("Order")
def test_order_create_empty_cart(auth_client):
    auth_client.clear_cart()

    resp, duration = auth_client.create_order()

    assert resp.status_code == 400
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/order/create", "POST", 400))
    assert body["error"] == "Cart is empty"
