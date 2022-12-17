from typing import TYPE_CHECKING, Optional, Type

import pytest
from pydantic import ValidationError

from starlite import Starlite, Template, TemplateConfig, get
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.contrib.mako import MakoTemplateEngine
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from pathlib import Path

    from starlite.template import TemplateEngineProtocol


def test_handler_raise_for_no_template_engine() -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="index.html", context={"ye": "yeeee"})

    with create_test_client(route_handlers=[invalid_path]) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template engine is not configured", "status_code": 500}


def test_engine_passed_to_callback(template_dir: "Path") -> None:
    received_engine: Optional[JinjaTemplateEngine] = None

    def callback(engine: JinjaTemplateEngine) -> None:
        nonlocal received_engine
        received_engine = engine

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


@pytest.mark.parametrize("engine", (JinjaTemplateEngine, MakoTemplateEngine))
def test_engine_instance(engine: Type["TemplateEngineProtocol"], template_dir: "Path") -> None:
    engine_instance = engine(template_dir)
    config = TemplateConfig(engine=engine_instance)
    assert config.engine_instance is engine_instance


@pytest.mark.parametrize("engine", (JinjaTemplateEngine, MakoTemplateEngine))
def test_directory_validation(engine: Type["TemplateEngineProtocol"], template_dir: "Path") -> None:
    with pytest.raises(ValidationError):
        TemplateConfig(engine=engine)
