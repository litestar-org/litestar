import os
from typing import Any

from starlite import Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
from starlite.testing import create_test_client


def test_jinja_template(tmpdir: Any) -> None:
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("<html>Injected? {{test}}</html>")

    nested_dir = os.path.join(tmpdir, "users")
    os.mkdir(nested_dir)
    nested_path = os.path.join(nested_dir, "nested.html")

    with open(nested_path, "w") as file:
        file.write("<html>Does nested dirs work? {{test}}</html>")

    @get(path="/")
    def index_handler() -> Template:
        return Template(name="index.html", context={"test": "yep"})

    @get(path="/nested")
    def nested_path_handler() -> Template:
        return Template(name="users/nested.html", context={"test": "yep"})

    with create_test_client(
        route_handlers=[index_handler, nested_path_handler],
        template_config=TemplateConfig(engine=JinjaTemplateEngine, directory=tmpdir),
    ) as client:
        index_response = client.request("GET", "/")
        assert index_response.status_code == 200
        assert index_response.text == "<html>Injected? yep</html>"
        assert index_response.headers["Content-Type"] == "text/html; charset=utf-8"

        nested_response = client.request("GET", "/nested")
        assert nested_response.status_code == 200
        assert nested_response.text == "<html>Does nested dirs work? yep</html>"
        assert nested_response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_jinja_raise_for_invalid_path(tmpdir: Any) -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="invalid.html", context={"test": "yep"})

    with create_test_client(
        route_handlers=[invalid_path],
        template_config=TemplateConfig(engine=JinjaTemplateEngine, directory=tmpdir),
    ) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template invalid.html not found.", "extra": None, "status_code": 500}


def test_mako_template(tmpdir: Any) -> None:
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("<html>Injected? ${test}</html>")

    nested_dir = os.path.join(tmpdir, "users")
    os.mkdir(nested_dir)
    nested_path = os.path.join(nested_dir, "nested.html")

    with open(nested_path, "w") as file:
        file.write("<html>Does nested dirs work? ${test}</html>")

    @get(path="/")
    def index_handler() -> Template:
        return Template(name="index.html", context={"test": "yep"})

    @get(path="/nested")
    def nested_path_handler() -> Template:
        return Template(name="users/nested.html", context={"test": "yep"})

    with create_test_client(
        route_handlers=[index_handler, nested_path_handler],
        template_config=TemplateConfig(engine=MakoTemplateEngine, directory=tmpdir),
    ) as client:
        index_response = client.request("GET", "/")
        assert index_response.status_code == 200
        assert index_response.text == "<html>Injected? yep</html>"
        assert index_response.headers["Content-Type"] == "text/html; charset=utf-8"

        nested_response = client.request("GET", "/nested")
        assert nested_response.status_code == 200
        assert nested_response.text == "<html>Does nested dirs work? yep</html>"
        assert nested_response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_mako_raise_for_invalid_path(tmpdir: Any) -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="invalid.html", context={"test": "yep"})

    with create_test_client(
        route_handlers=[invalid_path],
        template_config=TemplateConfig(engine=MakoTemplateEngine, directory=tmpdir),
    ) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template invalid.html not found.", "extra": None, "status_code": 500}


def test_handler_raise_for_no_template_engine() -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="index.html", context={"ye": "yeeee"})

    with create_test_client(route_handlers=[invalid_path]) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template engine is not configured", "extra": None, "status_code": 500}


def test_template_with_no_context(tmpdir: Any) -> None:
    path = os.path.join(tmpdir, "index.html")
    with open(path, "w") as file:
        file.write("<html>This works!</html>")

    @get(path="/")
    def index() -> Template:
        return Template(name="index.html")

    with create_test_client(
        route_handlers=[index],
        template_config=TemplateConfig(engine=JinjaTemplateEngine, directory=tmpdir),
    ) as client:
        index_response = client.request("GET", "/")
        assert index_response.status_code == 200
        assert index_response.text == "<html>This works!</html>"
        assert index_response.headers["Content-Type"] == "text/html; charset=utf-8"
