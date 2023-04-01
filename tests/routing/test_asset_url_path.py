from typing import TYPE_CHECKING

import pytest

from litestar import Litestar, get
from litestar.exceptions import NoRouteMatchFoundException
from litestar.static_files.config import StaticFilesConfig

if TYPE_CHECKING:
    from pathlib import Path


def test_url_for_static_asset(tmp_path: "Path") -> None:
    app = Litestar(
        route_handlers=[],
        static_files_config=[StaticFilesConfig(path="/static/path", directories=[tmp_path], name="asset")],
    )
    url_path = app.url_for_static_asset("asset", "abc/def.css")
    assert url_path == "/static/path/abc/def.css"


def test_url_for_static_asset_doesnt_work_with_http_handler_name(tmp_path: "Path") -> None:
    @get("/handler", name="handler")
    def handler() -> None:
        pass

    app = Litestar(
        route_handlers=[handler],
        static_files_config=[StaticFilesConfig(path="/static/path", directories=[tmp_path], name="asset")],
    )

    with pytest.raises(NoRouteMatchFoundException):
        app.url_for_static_asset("handler", "abc/def.css")


def test_url_for_static_asset_validates_name(tmp_path: "Path") -> None:
    app = Litestar(
        route_handlers=[],
        static_files_config=[StaticFilesConfig(path="/static/path", directories=[tmp_path], name="asset")],
    )

    with pytest.raises(NoRouteMatchFoundException):
        app.url_for_static_asset("non-existing-name", "abc/def.css")
