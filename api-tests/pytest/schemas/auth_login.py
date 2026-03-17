AUTH_LOGIN_SUCCESS_SCHEMA = {
  "type": "object",
  "properties": {
    "accessToken": {
      "type": "string",
      # Basic JWT format: header.payload.signature, each base64url characters
      "pattern": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
    },
    "tokenType": {
      "type": "string",
    },
  },
  "required": ["accessToken", "tokenType"],
  "additionalProperties": False,
}

AUTH_LOGIN_ERROR_SCHEMA = {
  "type": "object",
  "properties": {
    "message": {"type": "string"},
  },
  "required": ["message"],
  "additionalProperties": False,
}

