from unittest.mock import Mock, patch

import pytest
from orjson import JSONDecodeError

from starlite import Request


@pytest.mark.asyncio  # type: ignore[misc]
@patch.object(Request, "body", return_value=b"")
async def test_request_empty_body_to_json(mocked_request: Mock) -> None:
    request_empty_payload = Request(scope={"type": "http"})  # type: Request

    request_json = await request_empty_payload.json()

    assert request_json is None


@pytest.mark.asyncio  # type: ignore[misc]
@patch.object(Request, "body", return_value=b"invalid json")
async def test_request_invalid_body_to_json(mocked_request: Mock) -> None:
    request_empty_payload = Request(scope={"type": "http"})  # type: Request

    with pytest.raises(JSONDecodeError):
        await request_empty_payload.json()


@pytest.mark.asyncio  # type: ignore[misc]
@patch.object(Request, "body", return_value=b'{"test": "valid"}')
async def test_request_valid_body_to_json(mocked_request: Mock) -> None:
    request_empty_payload = Request(scope={"type": "http"})  # type: Request

    request_json = await request_empty_payload.json()
    assert request_json == {"test": "valid"}
