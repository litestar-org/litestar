from typing import Any, NoReturn

import pytest

from starlite import delete
from starlite.testing import create_test_client


@pytest.mark.parametrize("return_annotation", (None, NoReturn))
def test_handler_return_none_and_204_status_response_empty(return_annotation: Any) -> None:
    @delete(path="/")
    async def route() -> return_annotation:  # type: ignore[valid-type]
        return None

    with create_test_client(route_handlers=[route]) as client:
        response = client.delete("/")
        assert not response.content
