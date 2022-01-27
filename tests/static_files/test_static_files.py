import pytest
from pydantic import ValidationError

from starlite import create_test_client
from starlite.config import StaticFilesConfig


def test_staticfiles(tmpdir):
    path = tmpdir.join("test.txt")
    path.write("content")
    static_files_config = StaticFilesConfig(path="/static", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/static/test.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_staticfiles_for_slash_path(tmpdir):
    path = tmpdir.join("text.txt")
    path.write("content")

    static_files_config = StaticFilesConfig(path="/", directories=[tmpdir])
    with create_test_client([], static_files_config=static_files_config) as client:
        response = client.get("/text.txt")
        assert response.status_code == 200
        assert response.text == "content"


def test_config_validation(tmpdir):
    path = tmpdir.join("text.txt")
    path.write("content")

    with pytest.raises(ValidationError):
        StaticFilesConfig(path="", directories=[tmpdir])
