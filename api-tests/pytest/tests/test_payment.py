from jsonschema import validate

from schemas.order import ORDER_CREATE_SUCCESS_SCHEMA
from schemas.payment import PAYMENT_ERROR_SCHEMA, PAYMENT_SUCCESS_SCHEMA


def _create_order_and_get_id(auth_client) -> str:
  auth_client.clear_cart()
  add_resp, _ = auth_client.add_to_cart(product_id=1, quantity=1)
  assert add_resp.status_code == 201

  order_resp, _ = auth_client.create_order()
  assert order_resp.status_code == 201

  order_body = order_resp.json()
  validate(instance=order_body, schema=ORDER_CREATE_SUCCESS_SCHEMA)
  return order_body["orderId"]


def test_payment_success(auth_client):
  order_id = _create_order_and_get_id(auth_client)

  resp, duration = auth_client.charge_payment(order_id=order_id, card_number="4111111111111111")

  assert resp.status_code == 200
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=PAYMENT_SUCCESS_SCHEMA)
  assert body["orderId"] == order_id
  assert body["status"] == "PAID"


def test_payment_order_not_found(auth_client):
  resp, duration = auth_client.charge_payment(order_id="non-existent-order", card_number="4111")

  assert resp.status_code == 404
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=PAYMENT_ERROR_SCHEMA)
  assert body["error"] == "Order not found"


def test_payment_invalid_card_details(auth_client):
  order_id = _create_order_and_get_id(auth_client)

  resp, duration = auth_client.charge_payment(order_id=order_id, card_number="123")

  assert resp.status_code == 400
  assert duration < 0.5

