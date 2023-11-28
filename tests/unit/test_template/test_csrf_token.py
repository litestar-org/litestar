import html
from pathlib import Path
from typing import Any

import pytest

from litestar import MediaType, get
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.mako import MakoTemplateEngine
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.middleware.csrf import generate_csrf_token
from litestar.response.template import Template
from litestar.template.config import TemplateConfig
from litestar.testing import create_test_client
from litestar.types import Scope
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState


@pytest.mark.parametrize(
    "engine, template",
    (
        (JinjaTemplateEngine, "{{csrf_token()}}"),
        (MakoTemplateEngine, "${csrf_token()}"),
        (MiniJinjaTemplateEngine, "{{csrf_token()}}"),
    ),
)
def test_csrf_token(engine: Any, template: str, tmp_path: Path) -> None:
    Path(tmp_path / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(template_name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=tmp_path,
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
        (MiniJinjaTemplateEngine, "{{csrf_input}}"),
    ),
)
def test_csrf_input(engine: Any, template: str, tmp_path: Path) -> None:
    Path(tmp_path / "abc.html").write_text(template)
    token = {"value": ""}

    @get(path="/", media_type=MediaType.HTML)
    def handler(scope: Scope) -> Template:
        connection_state = ScopeState.from_scope(scope)
        token["value"] = value_or_default(connection_state.csrf_token, "")
        return Template(template_name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=tmp_path,
            engine=engine,
        ),
        csrf_config=csrf_config,
    ) as client:
        response = client.get("/")
        assert token["value"]
        assert html.unescape(response.text) == f'<input type="hidden" name="_csrf_token" value="{token["value"]}" />'
