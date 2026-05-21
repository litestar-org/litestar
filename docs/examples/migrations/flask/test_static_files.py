from litestar import Litestar
from litestar.static_files import create_static_files_router

app = Litestar(
    route_handlers=[
        create_static_files_router(path="/static", directories=["assets"]),
    ]
)

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


@pytest.fixture
def assets_cwd(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hello.txt").write_text("Hello, world!")
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(previous)


def test_serves_static_file(assets_cwd: Path) -> None:
    assert (assets_cwd / "assets" / "hello.txt").is_file()
    with TestClient(app) as client:
        response = client.get("/static/hello.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, world!"
