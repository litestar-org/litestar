import pytest
from litestar import Litestar
from litestar.exceptions import HTTPException
from starlette.status import HTTP_413_REQUEST_ENTITY_TOO_LARGE
from litestar.testing import create_test_client

# Define a proper handler at module level
async def upload_handler(data):
    return {"success": True}

@pytest.mark.anyio
async def test_oversized_file_returns_413():
    app = Litestar(
        route_handlers=[upload_handler],
        multipart_form_part_limit=10,  # Small limit to trigger the error
    )

    async with create_test_client(app) as client:
        response = await client.post("/upload", data={"file": "x" * 100})  # Example oversized data
        assert response.status_code == HTTP_413_REQUEST_ENTITY_TOO_LARGE
