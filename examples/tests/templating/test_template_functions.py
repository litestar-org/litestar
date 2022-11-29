from examples.templating.template_functions import app as app
from starlite import TestClient


def test_template_functions() -> None:
    with TestClient(app=app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.text == "<strong>check_context_key: </strong>nope"
