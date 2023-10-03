from docs.examples.templating.returning_templates_jinja import app as jinja_app
from docs.examples.templating.returning_templates_jinja import app as minijinja_app
from docs.examples.templating.returning_templates_mako import app as mako_app

from litestar.testing import TestClient


def test_returning_templates_jinja():
    with TestClient(jinja_app) as client:
        response = client.get("/", params={"name": "Jinja"})
        assert response.text == "Hello <strong>Jinja</strong>"


def test_returning_templates_mako():
    with TestClient(mako_app) as client:
        response = client.get("/", params={"name": "Mako"})
        assert response.text.strip() == "Hello <strong>Mako</strong>"


def test_returning_templates_minijinja():
    with TestClient(minijinja_app) as client:
        response = client.get("/", params={"name": "Minijinja"})
        assert response.text == "Hello <strong>Minijinja</strong>"
