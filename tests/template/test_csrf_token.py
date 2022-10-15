import html
from pathlib import Path
from typing import Any

import pytest

from starlite import CSRFConfig, MediaType, Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
from starlite.testing import create_test_client
from starlite.types import Scope
from starlite.utils import generate_csrf_token


@pytest.mark.parametrize(
    "engine, template",
    (
        (JinjaTemplateEngine, "{{csrf_token()}}"),
        (MakoTemplateEngine, "${csrf_token()}"),
    ),
)
def test_csrf_token(engine: Any, template: str, template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
        csrf_config=csrf_config,
    ) as client:
        response = client.get("/")
        assert len(response.text) == len(generate_csrf_token(csrf_config.secret))


@pytest.mark.parametrize(
    "engine, template",
    (
        (JinjaTemplateEngine, "{{csrf_input}}"),
        (MakoTemplateEngine, "${csrf_input}"),
    ),
)
def test_csrf_input(engine: Any, template: str, template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text(template)
    token = {"value": ""}

    @get(path="/", media_type=MediaType.HTML)
    def handler(scope: Scope) -> Template:
        token["value"] = scope.get("_csrf_token", "")  # type: ignore
        return Template(name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
        csrf_config=csrf_config,
    ) as client:
        response = client.get("/")
        assert token["value"]
        assert html.unescape(response.text) == f'<input type="hidden" name="_csrf_token" value="{token["value"]}" />'
