PAYMENT_SUCCESS_SCHEMA = {
  "type": "object",
  "properties": {
    "message": {"type": "string"},
    "orderId": {
      "type": "string",
      # should be the same format as orderId from order schema
      "pattern": r"^[0-9]+$",
    },
    "status": {"type": "string"},
  },
  "required": ["message", "orderId", "status"],
  "additionalProperties": False,
}

PAYMENT_ERROR_SCHEMA = {
  "type": "object",
  "properties": {"error": {"type": "string"}},
  "required": ["error"],
  "additionalProperties": False,
}

