import pytest
from docs.examples.templating.returning_templates_jinja import app as jinja_app
from docs.examples.templating.returning_templates_jinja import app as minijinja_app
from docs.examples.templating.returning_templates_mako import app as mako_app

from litestar.testing import TestClient


@pytest.mark.parametrize("template_type", ["file", "string"])
def test_returning_templates_jinja(template_type):
    with TestClient(jinja_app) as client:
        response = client.get(f"/{template_type}", params={"name": "Jinja"})
        if template_type == "file":
            assert response.text == "Hello <strong>Jinja</strong>"
        elif template_type == "string":
            assert response.text == "Hello <strong>Jinja</strong> using strings"


@pytest.mark.parametrize("template_type", ["file", "string"])
def test_returning_templates_mako(template_type):
    with TestClient(mako_app) as client:
        response = client.get(f"/{template_type}", params={"name": "Mako"})
        if template_type == "file":
            assert response.text == "Hello <strong>Mako</strong>\n"
        elif template_type == "string":
            assert response.text.strip() == "Hello <strong>Mako</strong> using strings"


@pytest.mark.parametrize("template_type", ["file", "string"])
def test_returning_templates_minijinja(template_type):
    with TestClient(minijinja_app) as client:
        response = client.get(f"/{template_type}", params={"name": "Minijinja"})
        if template_type == "file":
            assert response.text == "Hello <strong>Minijinja</strong>"
        elif template_type == "string":
            assert response.text.strip() == "Hello <strong>Minijinja</strong> using strings"
