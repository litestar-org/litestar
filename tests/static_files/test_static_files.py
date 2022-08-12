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


def test_staticfiles_html_mode(tmpdir: Any) -> None:
    path = tmpdir.join("index.html")
    path.write("content")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir], html_mode=True)
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static")
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

    with pytest.raises(ValidationError):
        StaticFilesConfig(path="/{param:int}", directories=[tmpdir])


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


def test_multiple_configs(tmpdir: Any) -> None:
    root1 = tmpdir.mkdir("1")
    root2 = tmpdir.mkdir("2")
    path1 = root1.join("test.txt")
    path1.write("content1")
    path2 = root2.join("test.txt")
    path2.write("content2")

    static_files_config = [
        StaticFilesConfig(path="/1", directories=[root1]),
        StaticFilesConfig(path="/2", directories=[root2]),
    ]
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/1/test.txt")
        assert response.status_code == 200
        assert response.text == "content1"

        response = client.get("/2/test.txt")
        assert response.status_code == 200
        assert response.text == "content2"


def test_static_substring_of_self(tmpdir: Any) -> None:
    path = tmpdir.mkdir("static_part").mkdir("static")
    path = path.join("test.txt")
    path.write("content")

    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/static_part/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"
