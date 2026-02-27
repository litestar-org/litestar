from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY

import pytest
import structlog

from litestar import Litestar, get
from litestar.middleware.logging import LoggingMiddleware
from litestar.testing import TestClient

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture(autouse=True)
def structlog_reset() -> Iterator[None]:
    try:
        yield
    finally:
        structlog.reset_defaults()


def test_structlog_to_file(tmp_path: Path) -> None:
    log_file = tmp_path / "log.log"

    with log_file.open("wt") as file_handle:
        structlog.reset_defaults()
        structlog.configure(
            logger_factory=structlog.WriteLoggerFactory(file=file_handle),
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.format_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
        )
        logger = structlog.getLogger("litestar.test")

        @get("/")
        def handler() -> str:
            logger.info("handled", hello="world")
            return "hello"

        app = Litestar(
            route_handlers=[handler],
            middleware=[LoggingMiddleware(logger, log_structured=True)],
            debug=True,
        )

        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.text == "hello"

    logged_data = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert logged_data == [
        {
            "path": "/",
            "method": "GET",
            "content_type": ["", {}],
            "query": {},
            "path_params": {},
            "event": "HTTP Request",
            "level": "info",
            "timestamp": ANY,
        },
        {"hello": "world", "event": "handled", "level": "info", "timestamp": ANY},
        {
            "status_code": 200,
            "event": "HTTP Response",
            "level": "info",
            "timestamp": ANY,
        },
    ]
