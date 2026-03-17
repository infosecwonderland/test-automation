PRODUCT_SCHEMA = {
  "type": "object",
  "properties": {
    "id": {
      "type": "integer",
      "minimum": 1,
    },
    "name": {
      "type": "string",
      # basic non-empty name
      "minLength": 1,
    },
    "price": {
      "type": "number",
      "minimum": 0,
    },
  },
  "required": ["id", "name", "price"],
  "additionalProperties": False,
}

PRODUCT_LIST_SCHEMA = {
  "type": "array",
  "items": PRODUCT_SCHEMA,
}

