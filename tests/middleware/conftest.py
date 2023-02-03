from typing import TYPE_CHECKING

import pytest

from starlite.config.logging import LoggingConfig, default_handlers

if TYPE_CHECKING:
    from starlite.types.callable_types import GetLogger


@pytest.fixture
def get_logger() -> "GetLogger":
    # due to the limitations of caplog we have to place this call here.
    # we also have to allow propagation.
    return LoggingConfig(
        handlers=default_handlers,
        loggers={
            "starlite": {"level": "DEBUG", "handlers": ["queue_listener"], "propagate": True},
        },
    ).configure()
