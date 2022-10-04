from typing import TYPE_CHECKING, Optional

from starlite import Starlite, Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.testing import create_test_client

if TYPE_CHECKING:
    import pathlib


def test_handler_raise_for_no_template_engine() -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="index.html", context={"ye": "yeeee"})

    with create_test_client(route_handlers=[invalid_path]) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template engine is not configured", "status_code": 500}


def test_engine_passed_to_callback(template_dir: "pathlib.Path") -> None:
    received_engine: Optional[JinjaTemplateEngine] = None

    def callback(engine: JinjaTemplateEngine) -> None:
        nonlocal received_engine
        received_engine = engine
        return None

    app = Starlite(
        route_handlers=[],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
            engine_callback=callback,
        ),
    )

    assert received_engine is not None
    assert received_engine is app.template_engine
