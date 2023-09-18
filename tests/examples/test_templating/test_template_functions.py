from docs.examples.templating.template_functions_jinja import app as jinja_app
from docs.examples.templating.template_functions_mako import app as mako_app
from docs.examples.templating.template_functions_minijinja import app as minijinja_app

from litestar.testing import TestClient


def test_template_functions_jinja():
    with TestClient(jinja_app) as client:
        response = client.get("/")
        assert response.text == "<strong>check_context_key: </strong>nope"


def test_template_functions_mako():
    with TestClient(mako_app) as client:
        response = client.get("/")
        assert response.text.strip() == "<strong>check_context_key: </strong>nope"


def test_template_functions_minijinja():
    with TestClient(minijinja_app) as client:
        response = client.get("/")
        assert response.text == "<strong>check_context_key: </strong>nope"
