import json

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.main import create_app


pytestmark = [pytest.mark.unit]


@pytest.mark.asyncio
async def test_validation_handler_serializes_ctx_values():
    app = create_app()
    handler = app.exception_handlers[RequestValidationError]

    non_serializable = object()
    error_payload = [
        {
            "loc": ("body", "field"),
            "msg": "Invalid value",
            "type": "type_error",
            "ctx": {"value": non_serializable},
        }
    ]
    exc = RequestValidationError(error_payload)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/crawl",
        "headers": [],
        "app": app,
    }
    request = Request(scope)

    response = await handler(request, exc)
    assert response.status_code == 422

    payload = json.loads(response.body)
    assert payload["detail"][0]["ctx"]["value"] == str(non_serializable)
