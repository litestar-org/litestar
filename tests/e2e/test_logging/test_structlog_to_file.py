from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY

import pytest
import structlog

from litestar import Litestar, Request, get
from litestar.logging.structlog import StructLoggingConfig
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

        @get("/")
        def handler(request: Request) -> str:
            request.logger.info("handled", hello="world")
            return "hello"

        app = Litestar(
            route_handlers=[handler],
            middleware=[LoggingMiddleware()],
            logging_config=StructLoggingConfig(
                logger_factory=structlog.WriteLoggerFactory(file=file_handle),
            ),
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
            "headers": {
                "host": "testserver.local",
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br, zstd",
                "connection": "keep-alive",
                "user-agent": "testclient",
            },
            "cookies": {},
            "query": {},
            "path_params": {},
            "body": None,
            "event": "HTTP Request",
            "level": "info",
            "timestamp": ANY,
        },
        {"hello": "world", "event": "handled", "level": "info", "timestamp": ANY},
        {
            "status_code": 200,
            "cookies": {},
            "headers": {"content-type": "text/plain; charset=utf-8", "content-length": "5"},
            "body": "hello",
            "event": "HTTP Response",
            "level": "info",
            "timestamp": ANY,
        },
    ]
