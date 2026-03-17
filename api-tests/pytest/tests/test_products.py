from jsonschema import validate

from schemas.products import PRODUCT_LIST_SCHEMA


def test_get_products_success(client):
  resp, duration = client.get_products()

  assert resp.status_code == 200
  assert duration < 0.5

  body = resp.json()
  validate(instance=body, schema=PRODUCT_LIST_SCHEMA)
  assert len(body) >= 1

