from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import ANY

import pytest
import structlog

from litestar import Litestar, get
from litestar.logging import StructLoggingConfig
from litestar.logging.config import default_json_serializer, default_structlog_processors
from litestar.plugins.structlog import StructlogConfig, StructlogPlugin
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

    logging_config = StructlogConfig(
        structlog_logging_config=StructLoggingConfig(
            logger_factory=structlog.WriteLoggerFactory(file=log_file.open("wt")),
            processors=default_structlog_processors(
                json_serializer=lambda v, **_: str(default_json_serializer(v), "utf-8")
            ),
        ),
    )

    logger = structlog.get_logger()

    @get("/")
    def handler() -> str:
        logger.info("handled", hello="world")
        return "hello"

    app = Litestar(route_handlers=[handler], plugins=[StructlogPlugin(config=logging_config)], debug=True)

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
                "accept-encoding": "gzip, deflate, br",
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
