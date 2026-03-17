import allure

from jsonschema import validate

from utils.contract_loader import response_schema


def _create_order(auth_client) -> str:
    auth_client.clear_cart()
    add_resp, _ = auth_client.add_to_cart(product_id=1, quantity=1)
    assert add_resp.status_code == 201

    order_resp, _ = auth_client.create_order()
    assert order_resp.status_code == 201

    body = order_resp.json()
    validate(instance=body, schema=response_schema("/order/create", "POST", 201))
    return body["orderId"]


@allure.feature("API Tests")
@allure.story("Payment")
def test_payment_success(auth_client):
    order_id = _create_order(auth_client)

    resp, duration = auth_client.charge_payment(order_id=order_id, card_number="4111111111111111")

    assert resp.status_code == 200
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/payment/charge", "POST", 200))
    assert body["orderId"] == order_id
    assert body["status"] == "PAID"


@allure.feature("API Tests")
@allure.story("Payment")
def test_payment_order_not_found(auth_client):
    resp, duration = auth_client.charge_payment(order_id="non-existent-order", card_number="4111")

    assert resp.status_code == 404
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/payment/charge", "POST", 404))
    assert body["error"] == "Order not found"


@allure.feature("API Tests")
@allure.story("Payment")
def test_payment_invalid_card_details(auth_client):
    order_id = _create_order(auth_client)

    resp, duration = auth_client.charge_payment(order_id=order_id, card_number="123")

    assert resp.status_code == 400
    assert duration < 0.5
