from litestar import Litestar
from litestar.static_files import create_static_files_router

app = Litestar(
    route_handlers=[
        create_static_files_router(path="/static", directories=["assets"]),
    ]
)

from pathlib import Path

import pytest

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


@pytest.fixture
def static_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Litestar:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hello.txt").write_text("Hello, world!")
    monkeypatch.chdir(tmp_path)
    return Litestar(
        route_handlers=[
            create_static_files_router(path="/static", directories=["assets"]),
        ]
    )


def test_serves_static_file(static_app: Litestar) -> None:
    with TestClient(static_app) as client:
        response = client.get("/static/hello.txt")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, world!"
