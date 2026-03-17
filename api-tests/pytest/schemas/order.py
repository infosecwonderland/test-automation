ORDER_CREATE_SUCCESS_SCHEMA = {
  "type": "object",
  "properties": {
    "message": {"type": "string"},
    "orderId": {
      "type": "string",
      # current SUT uses Date.now().toString(), so digits only
      "pattern": r"^[0-9]+$",
    },
    "total": {"type": "number"},
  },
  "required": ["message", "orderId", "total"],
  "additionalProperties": False,
}

ORDER_ERROR_SCHEMA = {
  "type": "object",
  "properties": {"error": {"type": "string"}},
  "required": ["error"],
  "additionalProperties": False,
}

