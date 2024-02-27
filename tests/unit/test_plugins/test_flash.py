from enum import Enum
from pathlib import Path

import pytest

from litestar import Request, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.mako import MakoTemplateEngine
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.plugins.flash import FlashConfig, FlashDefaultCategory, FlashPlugin, flash
from litestar.response import Template
from litestar.template import TemplateConfig, TemplateEngineProtocol
from litestar.testing import create_test_client

text_html_jinja = """{% for message in get_flashes() %}<span class="{{ message.category }}">{{ message.message }}</span>{% endfor %}"""
text_html_mako = """<% messages = get_flashes() %>\\
% for m in messages:
<span class="${m['category']}">${m['message']}</span>\\
% endfor
"""


class CustomCategory(str, Enum):
    custom1 = "custom1"
    custom2 = "custom2"
    custom3 = "custom3"
    custom4 = "custom4"


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
    (FlashDefaultCategory, CustomCategory),
    ids=("default_category", "custom_category"),
)
def test_flash_plugin(
    tmp_path: Path,
    engine: type[TemplateEngineProtocol],
    template_str: str,
    category_enum: Enum,
) -> None:
    Path(tmp_path / "flash.html").write_text(template_str)
    text_expected = "".join(
        [f'<span class="{category.value}">message {category.value}</span>' for category in category_enum.__members__.values()]
    )

    @get("/flash")
    def flash_handler(request: Request) -> Template:
        for category in category_enum:
            flash(request, f"message {category.value}", category=category.value)
        return Template("flash.html")

    template_config = TemplateConfig(
        directory=Path(tmp_path),
        engine=engine,
    )
    with create_test_client(
        [flash_handler],
        template_config=template_config,
        plugins=[FlashPlugin(config=FlashConfig(template_config=template_config))],
    ) as client:
        r = client.get("/flash")
        assert r.status_code == 200
        assert r.text == text_expected
