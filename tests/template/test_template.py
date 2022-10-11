from pathlib import Path
from typing import Optional
from unittest.mock import patch

from starlite import Starlite, Template, TemplateConfig, get
from starlite.connection import Request
from starlite.template.jinja import JinjaTemplateEngine
from starlite.testing import create_test_client


def test_handler_raise_for_no_template_engine() -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="index.html", context={"ye": "yeeee"})

    with create_test_client(route_handlers=[invalid_path]) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template engine is not configured", "status_code": 500}


def test_engine_passed_to_callback(template_dir: Path) -> None:
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


def test_template_response_receives_request_in_context(template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text("")

    @get(path="/")
    def handler() -> Template:
        return Template(name="abc.html", context={})

    with patch("starlite.response.TemplateResponse") as template_response_mock, create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
    ) as client:
        client.request("GET", "/")
        assert template_response_mock.called

        _, kwargs = template_response_mock.call_args
        context = kwargs.get("context")
        request = context.get("request")

        assert isinstance(request, Request)


def test_request_can_not_be_overridden_in_context(template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text("")

    @get(path="/")
    def handler() -> Template:
        return Template(name="abc.html", context={"request": 123})

    with patch("starlite.response.TemplateResponse") as template_response_mock, create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
    ) as client:

        client.request("GET", "/")
        assert template_response_mock.called

        _, kwargs = template_response_mock.call_args
        context = kwargs.get("context")
        request = context.get("request")

        assert isinstance(request, Request)
