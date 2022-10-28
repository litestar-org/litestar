from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from starlite import ImproperlyConfiguredException, MediaType, Starlite, get
from starlite.config import StaticFilesConfig
from starlite.status_codes import HTTP_200_OK
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from pathlib import Path


def test_staticfiles_standard_config(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])

    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_staticfiles_html_mode(tmpdir: "Path") -> None:
    path = tmpdir / "index.html"
    path.write_text("content", "utf-8")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir], html_mode=True)
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static")
        assert response.status_code == 200
        assert response.text == "content"


def test_staticfiles_for_slash_path(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/text.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_config_validation(tmpdir: "Path") -> None:
    path = tmpdir / "text.txt"
    path.write_text("content", "utf-8")

    with pytest.raises(ValidationError):
        StaticFilesConfig(path="", directories=[tmpdir])

    with pytest.raises(ValidationError):
        StaticFilesConfig(path="/{param:int}", directories=[tmpdir])


def test_sub_path_under_static_path(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/static/sub/{f:str}", media_type=MediaType.TEXT)
    def handler(f: str) -> str:
        return f

    with create_test_client(
        handler, static_files_config=StaticFilesConfig(path="/static", directories=[tmpdir])
    ) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == HTTP_200_OK

        response = client.get("/static/sub/abc")
        assert response.status_code == HTTP_200_OK


def test_validation_of_static_path_and_path_parameter(tmpdir: "Path") -> None:
    path = tmpdir / "test.txt"
    path.write_text("content", "utf-8")

    @get("/static/{f:str}", media_type=MediaType.TEXT)
    def handler(f: str) -> str:
        return f

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler], static_files_config=StaticFilesConfig(path="/static", directories=[tmpdir]))


def test_multiple_configs(tmpdir: "Path") -> None:
    root1 = tmpdir.mkdir("1")  # type: ignore
    root2 = tmpdir.mkdir("2")  # type: ignore
    path1 = root1 / "test.txt"  # pyright: ignore
    path1.write_text("content1", "utf-8")
    path2 = root2 / "test.txt"  # pyright: ignore
    path2.write_text("content2", "utf-8")

    static_files_config = [
        StaticFilesConfig(path="/1", directories=[root1]),  # pyright: ignore
        StaticFilesConfig(path="/2", directories=[root2]),  # pyright: ignore
    ]
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/1/test.txt")
        assert response.status_code == 200
        assert response.text == "content1"

        response = client.get("/2/test.txt")
        assert response.status_code == 200
        assert response.text == "content2"


def test_static_substring_of_self(tmpdir: "Path") -> None:
    path = tmpdir.mkdir("static_part").mkdir("static") / "test.txt"  # type: ignore
    path.write_text("content", "utf-8")

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"
