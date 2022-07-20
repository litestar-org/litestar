import sys
from unittest import skipIf
from unittest.mock import patch

import pytest
from orjson import JSONDecodeError

from starlite.connection import Request


@skipIf(sys.version_info < (3, 8), "skipping due to python 3.7 async failures")
@pytest.mark.asyncio
async def test_request_empty_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b""):
        request_empty_payload: Request = Request(scope={"type": "http"})
        request_json = await request_empty_payload.json()
        assert request_json is None


@skipIf(sys.version_info < (3, 8), "skipping due to python 3.7 async failures")
@pytest.mark.asyncio
async def test_request_invalid_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b"invalid"), pytest.raises(JSONDecodeError):
        request_empty_payload: Request = Request(scope={"type": "http"})
        await request_empty_payload.json()


@skipIf(sys.version_info < (3, 8), "skipping due to python 3.7 async failures")
@pytest.mark.asyncio
async def test_request_valid_body_to_json() -> None:
    with patch.object(Request, "body", return_value=b'{"test": "valid"}'):
        request_empty_payload: Request = Request(scope={"type": "http"})
        request_json = await request_empty_payload.json()
        assert request_json == {"test": "valid"}
