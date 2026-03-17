"""
contract_loader.py
------------------
Parses sut/openapi/gateway.yaml using the openapi3 library.

Shared by both the API test suite and the security test suite.
Adding a new endpoint to gateway.yaml automatically includes it in all
relevant security checks and provides its response schemas for API tests.
"""

import os
from typing import Optional

import openapi3
import yaml

_SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "sut", "openapi", "gateway.yaml"
)

_TEST_EMAIL = os.getenv("SUT_TEST_EMAIL", "test@example.com")
_TEST_PASSWORD = os.getenv("SUT_TEST_PASSWORD", "password123")

_HTTP_METHODS = ["get", "post", "put", "patch", "delete"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> openapi3.OpenAPI:
    with open(_SPEC_PATH) as fh:
        return openapi3.OpenAPI(yaml.safe_load(fh))


def _schema_to_dict(schema) -> dict:
    """Recursively convert an openapi3 Schema object to a jsonschema-compatible dict."""
    if schema is None:
        return {}
    result = {}
    if schema.type:
        result["type"] = schema.type
    if schema.format:
        result["format"] = schema.format
    if schema.pattern:
        result["pattern"] = schema.pattern
    if schema.minimum is not None:
        result["minimum"] = schema.minimum
    if schema.minLength is not None:
        result["minLength"] = schema.minLength
    if schema.properties:
        result["properties"] = {
            name: _schema_to_dict(prop)
            for name, prop in schema.properties.items()
        }
    if schema.required:
        result["required"] = list(schema.required)
    if schema.items is not None:
        result["items"] = _schema_to_dict(schema.items)
    return result


def _sample_body(schema) -> dict:
    """Build a minimal valid request body from an openapi3 Schema object."""
    if schema is None or schema.type != "object":
        return {}
    body = {}
    for name, prop in (schema.properties or {}).items():
        if prop.type == "string":
            if prop.format == "email":
                body[name] = _TEST_EMAIL
            elif (prop.minLength or 0) >= 8:
                body[name] = _TEST_PASSWORD
            else:
                body[name] = "test-value-1"
        elif prop.type == "integer":
            body[name] = 1
        elif prop.type == "number":
            body[name] = 1.0
    return body


def _string_fields(schema) -> list:
    """Return names of all string-typed properties in an openapi3 Schema object."""
    if schema is None or schema.type != "object":
        return []
    return [
        name
        for name, prop in (schema.properties or {}).items()
        if prop.type == "string"
    ]


def _body_schema(operation) -> Optional[object]:
    if operation.requestBody is None:
        return None
    content = operation.requestBody.content
    if "application/json" not in content:
        return None
    return content["application/json"].schema


def _is_auth_required(operation) -> bool:
    return bool(operation.security)


def _resolve_path(path: str, operation) -> str:
    """Replace path parameter templates with dummy values based on schema type."""
    for param in (operation.parameters or []):
        if param.in_ != "path":
            continue
        ptype = param.schema.type if param.schema else "string"
        dummy = "0" if ptype == "integer" else "test-value"
        path = path.replace(f"{{{param.name}}}", dummy)
    return path


def _operations(api: openapi3.OpenAPI):
    """Yield (path, method, operation) for every defined HTTP operation."""
    for path, path_item in api.paths.items():
        for method in _HTTP_METHODS:
            operation = getattr(path_item, method, None)
            if operation is not None:
                yield path, method.upper(), operation


# ---------------------------------------------------------------------------
# Security test helpers
# ---------------------------------------------------------------------------

def auth_required_endpoints() -> list:
    """All endpoints that declare security: [{bearerAuth: []}]."""
    api = _load()
    results = []
    for path, method, op in _operations(api):
        if not _is_auth_required(op):
            continue
        body = _sample_body(_body_schema(op))
        results.append({
            "method": method,
            "path": _resolve_path(path, op),
            "body": body or None,
        })
    return results


def rate_limited_endpoints() -> list:
    """All endpoints tagged x-rate-limited: true in the spec."""
    api = _load()
    results = []
    for path, method, op in _operations(api):
        if not op.extensions.get("rate-limited"):
            continue
        override = op.extensions.get("rate-limit-body")
        body = override if override else _sample_body(_body_schema(op))
        results.append({
            "method": method,
            "path": _resolve_path(path, op),
            "body": body or None,
            "auth_required": _is_auth_required(op),
        })
    return results


def injectable_endpoints() -> list:
    """All (endpoint, field) pairs where the request body contains a string field."""
    api = _load()
    results = []
    for path, method, op in _operations(api):
        schema = _body_schema(op)
        fields = _string_fields(schema)
        if not fields:
            continue
        base = _sample_body(schema)
        auth = _is_auth_required(op)
        resolved_path = _resolve_path(path, op)
        for field in fields:
            results.append({
                "method": method,
                "path": resolved_path,
                "field": field,
                "base_body": base,
                "auth_required": auth,
            })
    return results


# ---------------------------------------------------------------------------
# API test helpers
# ---------------------------------------------------------------------------

def response_schema(path: str, method: str, status_code: int) -> dict:
    """
    Return the JSON Schema dict for a given endpoint's response.

    Derived directly from the OpenAPI spec — no manually maintained
    schema files needed.

    Example:
        validate(instance=body, schema=response_schema('/auth/login', 'POST', 200))
    """
    api = _load()
    path_item = api.paths.get(path)
    if path_item is None:
        raise KeyError(f"Path {path!r} not found in spec")
    operation = getattr(path_item, method.lower(), None)
    if operation is None:
        raise KeyError(f"Method {method} not defined for {path!r}")
    response = operation.responses.get(str(status_code))
    if response is None:
        raise KeyError(f"Status {status_code} not defined for {method} {path}")
    content = response.content
    if not content or "application/json" not in content:
        return {}
    return _schema_to_dict(content["application/json"].schema)
