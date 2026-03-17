from jsonschema import validate

from schemas.order import ORDER_CREATE_SUCCESS_SCHEMA, ORDER_ERROR_SCHEMA


def test_order_create_success(auth_client):
  # start from empty cart
  auth_client.clear_cart()
  # add one product then create order
  add_resp, _ = auth_client.add_to_cart(product_id=1, quantity=2)
  assert add_resp.status_code == 201

  resp, duration = auth_client.create_order()

  assert resp.status_code == 201
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=ORDER_CREATE_SUCCESS_SCHEMA)
  assert body["message"] == "Order created"
  assert isinstance(body["orderId"], str)
  assert body["total"] > 0


def test_order_create_empty_cart(auth_client):
  auth_client.clear_cart()

  resp, duration = auth_client.create_order()

  assert resp.status_code == 400
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=ORDER_ERROR_SCHEMA)
  assert body["error"] == "Cart is empty"

