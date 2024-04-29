from __future__ import annotations

from enum import Enum
from pathlib import Path

import pytest

from litestar import Litestar, Request, get, post
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.mako import MakoTemplateEngine
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.exceptions import ImproperlyConfiguredException
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.plugins.flash import FlashConfig, FlashPlugin, flash
from litestar.response import Redirect, Template
from litestar.template import TemplateConfig, TemplateEngineProtocol
from litestar.testing import create_test_client

text_html_jinja = """{% for message in get_flashes() %}<span class="{{ message.category }}">{{ message.message }}</span>{% endfor %}"""
text_html_mako = """<% messages = get_flashes() %>\\
% for m in messages:
<span class="${m['category']}">${m['message']}</span>\\
% endfor
"""


class CustomCategory(str, Enum):
    custom1 = "1"
    custom2 = "2"
    custom3 = "3"


class FlashCategory(str, Enum):
    info = "INFO"
    error = "ERROR"
    warning = "WARNING"
    success = "SUCCESS"


@pytest.mark.parametrize(
    "engine, template_str",
    (
        (JinjaTemplateEngine, text_html_jinja),
        (MakoTemplateEngine, text_html_mako),
        (MiniJinjaTemplateEngine, text_html_jinja),
    ),
    ids=("jinja", "mako", "minijinja"),
)
@pytest.mark.parametrize(
    "category_enum",
    (CustomCategory, FlashCategory),
    ids=("custom_category", "flash_category"),
)
def test_flash_plugin(
    tmp_path: Path,
    engine: type[TemplateEngineProtocol],
    template_str: str,
    category_enum: Enum,
) -> None:
    Path(tmp_path / "flash.html").write_text(template_str)

    @get("/")
    async def index() -> Redirect:
        return Redirect("/login")

    @get("/login")
    async def login(request: Request) -> Template:
        flash(request, "Flash Test!", category="info")
        return Template("flash.html")

    @post("/check")
    async def check(request: Request) -> Redirect:
        flash(request, "User not Found!", category="warning")
        return Redirect("/login")

    template_config: TemplateConfig = TemplateConfig(
        directory=Path(tmp_path),
        engine=engine,
    )
    session_config = ServerSideSessionConfig()
    flash_config = FlashConfig(template_config=template_config)
    with create_test_client(
        plugins=[FlashPlugin(config=flash_config)],
        route_handlers=[index, login, check],
        template_config=template_config,
        middleware=[session_config.middleware],
    ) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "Flash Test!" in r.text
        r = client.get("/login")
        assert r.status_code == 200
        assert "Flash Test!" in r.text
        r = client.post("/check")
        assert r.status_code == 200
        assert "User not Found!" in r.text
        assert "Flash Test!" in r.text


def test_flash_config_doesnt_have_session() -> None:
    template_config = TemplateConfig(directory=Path("tests/templates"), engine=JinjaTemplateEngine)
    flash_config = FlashConfig(template_config=template_config)
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(plugins=[FlashPlugin(config=flash_config)])


def test_flash_config_has_wrong_middleware_type() -> None:
    template_config = TemplateConfig(directory=Path("tests/templates"), engine=JinjaTemplateEngine)
    flash_config = FlashConfig(template_config=template_config)
    rate_limit_config = RateLimitConfig(rate_limit=("minute", 1), exclude=["/schema"])
    with pytest.raises(ImproperlyConfiguredException):
        Litestar(plugins=[FlashPlugin(config=flash_config)], middleware=[rate_limit_config.middleware])
