from typing import Union
from unittest.mock import MagicMock

import pytest

from litestar import get
from litestar.exceptions import HTTPException, ImproperlyConfiguredException, NotFoundException
from litestar.logging.config import LoggingConfig
from litestar.testing import create_test_client


@pytest.mark.parametrize(
    "disable_stack_trace, exception_to_raise, handler_called",
    [
        # will log the stack trace
        [set(), HTTPException, True],
        [set(), ValueError, True],
        [{400}, HTTPException, True],
        [{NameError}, ValueError, True],
        [{400, NameError}, ValueError, True],
        # will not log the stack trace
        [{NotFoundException}, HTTPException, False],
        [{404}, HTTPException, False],
        [{ValueError}, ValueError, False],
        [{400, ValueError}, ValueError, False],
        [{404, NameError}, HTTPException, False],
    ],
)
def test_disable_stack_trace(
    disable_stack_trace: set[Union[int, type[Exception]]],
    exception_to_raise: type[Exception],
    handler_called: bool,
) -> None:
    mock_handler = MagicMock()

    logging_config = LoggingConfig(disable_stack_trace=disable_stack_trace, exception_logging_handler=mock_handler)

    @get("/error")
    async def error_route() -> None:
        raise exception_to_raise

    with create_test_client([error_route], logging_config=logging_config, debug=True) as client:
        if exception_to_raise is HTTPException:
            _ = client.get("/404-error")
        else:
            _ = client.get("/error")

        if handler_called:
            assert mock_handler.called, "Exception logging handler should have been called"
        else:
            assert not mock_handler.called, "Exception logging handler should not have been called"
