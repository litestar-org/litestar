from __future__ import annotations

from pathlib import Path
from typing import Optional

from litestar import Litestar, get
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get(path="/{template_type: str}", sync_to_thread=False)
def index(name: str, template_type: Optional[str]) -> Template:  # noqa: UP007
    if template_type == "file":
        return Template(template_name="hello.html.minijinja", context={"name": name})
    elif template_type == "string":
        return Template(template_str="Hello <strong>Minijinja</strong> using strings", context={"name": name})
    elif not template_type:
        # Return something that should raise an error
        return Template(template_str=None)


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path(__file__).parent / "templates",
        engine=MiniJinjaTemplateEngine,
    ),
)
