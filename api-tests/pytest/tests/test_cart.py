from jsonschema import validate

from utils.contract_loader import response_schema


def test_add_to_cart_success(auth_client):
    auth_client.clear_cart()

    resp, duration = auth_client.add_to_cart(product_id=1, quantity=1)

    assert resp.status_code == 201
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/cart/add", "POST", 201))
    assert body["message"] == "Item added to cart"
    assert len(body["cart"]) == 1


def test_add_to_cart_invalid_product(auth_client):
    resp, duration = auth_client.add_to_cart(product_id=9999, quantity=1)

    assert resp.status_code == 400
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/cart/add", "POST", 400))
    assert body["error"] == "Invalid productId"


def test_add_to_cart_invalid_quantity(auth_client):
    resp, duration = auth_client.add_to_cart(product_id=1, quantity=0)

    assert resp.status_code == 400
    assert duration < 0.5

    body = resp.json()
    validate(instance=body, schema=response_schema("/cart/add", "POST", 400))
    assert body["error"] == "Invalid quantity"
