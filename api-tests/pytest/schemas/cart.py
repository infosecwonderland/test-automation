ADD_TO_CART_SUCCESS_SCHEMA = {
  "type": "object",
  "properties": {
    "message": {"type": "string"},
    "cart": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "productId": {
            "type": "integer",
            "minimum": 1,
          },
          "quantity": {
            "type": "integer",
            "minimum": 1,
          },
        },
        "required": ["productId", "quantity"],
        "additionalProperties": False,
      },
    },
  },
  "required": ["message", "cart"],
  "additionalProperties": False,
}

CART_ERROR_SCHEMA = {
  "type": "object",
  "properties": {"error": {"type": "string"}},
  "required": ["error"],
  "additionalProperties": False,
}

