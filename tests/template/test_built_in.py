import pathlib
from dataclasses import dataclass
from typing import Any, Type, Union

import pytest

from starlite import HTTPRouteHandler, Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
from starlite.testing import create_test_client


@dataclass
class EngineTest:
    engine: Type[Union[JinjaTemplateEngine, MakoTemplateEngine]]
    index_template: str
    nested_template: str


@pytest.fixture(
    params=[
        EngineTest(
            engine=JinjaTemplateEngine,
            index_template="<html>Injected? {{test}}</html>",
            nested_template="<html>Does nested dirs work? {{test}}</html>",
        ),
        EngineTest(
            engine=MakoTemplateEngine,
            index_template="<html>Injected? ${test}</html>",
            nested_template="<html>Does nested dirs work? ${test}</html>",
        ),
    ]
)
def engine_test(request: Any) -> EngineTest:
    return request.param  # type:ignore[no-any-return]


@pytest.fixture
def index_handler(engine_test: EngineTest, template_dir: pathlib.Path) -> HTTPRouteHandler:
    with open(template_dir / "index.html", "w") as f:
        f.write(engine_test.index_template)

    @get(path="/")
    def index_handler() -> Template:
        return Template(name="index.html", context={"test": "yep"})

    return index_handler


@pytest.fixture
def nested_path_handler(engine_test: EngineTest, template_dir: pathlib.Path) -> HTTPRouteHandler:
    nested_path = template_dir / "nested-dir"
    nested_path.mkdir()
    with open(nested_path / "nested.html", "w") as f:
        f.write(engine_test.nested_template)

    @get(path="/nested")
    def nested_path_handler() -> Template:
        return Template(name="nested-dir/nested.html", context={"test": "yep"})

    return nested_path_handler


@pytest.fixture
def template_config(engine_test: EngineTest, template_dir: pathlib.Path) -> TemplateConfig:
    return TemplateConfig(engine=engine_test.engine, directory=template_dir)


def test_template(index_handler: HTTPRouteHandler, template_config: TemplateConfig) -> None:
    with create_test_client(route_handlers=[index_handler], template_config=template_config) as client:
        response = client.request("GET", "/")
        assert response.status_code == 200, response.text
        assert response.text == "<html>Injected? yep</html>"
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_nested_template_directory(nested_path_handler: HTTPRouteHandler, template_config: TemplateConfig) -> None:
    with create_test_client(route_handlers=[nested_path_handler], template_config=template_config) as client:
        response = client.request("GET", "/nested")
        assert response.status_code == 200, response.text
        assert response.text == "<html>Does nested dirs work? yep</html>"
        assert response.headers["Content-Type"] == "text/html; charset=utf-8"


def test_raise_for_invalid_template_name(template_config: TemplateConfig) -> None:
    @get(path="/")
    def invalid_template_name_handler() -> Template:
        return Template(name="invalid.html", context={"test": "yep"})

    with create_test_client(route_handlers=[invalid_template_name_handler], template_config=template_config) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template invalid.html not found.", "extra": None, "status_code": 500}


def test_no_context(template_dir: pathlib.Path, template_config: TemplateConfig) -> None:
    with open(template_dir / "index.html", "w") as file:
        file.write("<html>This works!</html>")

    @get(path="/")
    def index() -> Template:
        return Template(name="index.html")

    with create_test_client(route_handlers=[index], template_config=template_config) as client:
        index_response = client.request("GET", "/")
        assert index_response.status_code == 200
        assert index_response.text == "<html>This works!</html>"
        assert index_response.headers["Content-Type"] == "text/html; charset=utf-8"
