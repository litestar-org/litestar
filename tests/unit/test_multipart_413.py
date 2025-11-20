"""Test that multipart file size limits return HTTP 413."""
import pytest
from litestar import post, Litestar
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.status_codes import HTTP_413_REQUEST_ENTITY_TOO_LARGE
from litestar.testing import create_test_client


# Define handler outside the test function to avoid pickling issues
@post("/upload")
async def upload_handler(
    data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART)
) -> dict:
    """Handle file uploads - expects multipart form data."""
    return {"filename": data.filename}


def test_oversized_file_returns_413():
    """Test that files exceeding part count limit return 413."""

    with create_test_client(
        route_handlers=[upload_handler],
        multipart_form_part_limit=2,  # Only allow 2 parts
    ) as client:
        # Create multiple files to exceed the part limit (3 files > 2 limit)
        response = client.post(
            "/upload",
            files={
                "file1": ("test1.txt", b"content1"),
                "file2": ("test2.txt", b"content2"),
                "data": ("test3.txt", b"content3"),  # 3rd part exceeds limit of 2
            },
        )

        # Should return 413, not 400
        assert response.status_code == HTTP_413_REQUEST_ENTITY_TOO_LARGE


if __name__ == "__main__":
    test_oversized_file_returns_413()
    print("Test completed!")
