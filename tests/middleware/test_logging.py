from unittest.mock import Mock, patch

from starlite import get
from starlite.testing import create_test_client


@get(path="/")
def get_handler() -> None:
    return None


@patch("starlite.middleware.logging.logger")
def test_logging_successful_flow(logger_mock: Mock) -> None:
    with create_test_client(route_handlers=[get_handler]) as client:
        client.get("/")
        assert logger_mock.info.call_count == 2
