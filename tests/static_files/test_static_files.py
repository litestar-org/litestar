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
