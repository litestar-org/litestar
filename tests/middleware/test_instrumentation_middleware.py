import logging
from typing import Any, cast

import pytest
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp

from starlite import get
from starlite.config import InstrumentationBackend, InstrumentationConfig
from starlite.middleware.instrumentation.base import InstrumentationMiddleware
from starlite.middleware.instrumentation.opentelemetry import OpenTelemetryMiddleware
from starlite.testing import create_test_client

logger = logging.getLogger(__name__)


@get(path="/")
def handler() -> PlainTextResponse:
    return PlainTextResponse("_starlite_" * 4000, status_code=200)


def test_invalid_instrumentation_middleware_backend() -> None:

    try:
        create_test_client(route_handlers=[handler], instrumentation_config=InstrumentationConfig(backend="oracle-oem"))
    except Exception as exc:
        assert isinstance(exc, ValueError)
