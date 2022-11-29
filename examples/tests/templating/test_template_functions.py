from examples.templating.template_functions import app as app
from starlite import TestClient


def test_template_functions() -> None:
    with TestClient(app=app) as client:
        pass


