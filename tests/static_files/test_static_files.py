from typing import Any

import pytest
from pydantic import ValidationError

from starlite import ImproperlyConfiguredException, Starlite, get
from starlite.config import StaticFilesConfig
from starlite.testing import create_test_client


def test_staticfiles(tmpdir: Any) -> None:
    path = tmpdir.join("test.txt")
    path.write("content")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_staticfiles_for_slash_path(tmpdir: Any) -> None:
    path = tmpdir.join("text.txt")
    path.write("content")

    static_files_config = StaticFilesConfig(path="/", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/text.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_config_validation(tmpdir: Any) -> None:
    path = tmpdir.join("text.txt")
    path.write("content")

    with pytest.raises(ValidationError):
        StaticFilesConfig(path="", directories=[tmpdir])


def test_path_inside_static(tmpdir: Any) -> None:
    path = tmpdir.join("test.txt")
    path.write("content")

    @get("/static/strange/{f:str}")
    def handler(f: str) -> str:
        return f

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[handler], static_files_config=static_files_config)

    app = Starlite(route_handlers=[], static_files_config=static_files_config)
    with pytest.raises(ImproperlyConfiguredException):
        app.register(handler)


def test_static_substring_of_self(tmpdir: Any) -> None:
    path = tmpdir.mkdir("static_part").mkdir("static")
    path = path.join("test.txt")
    path.write("content")

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"
