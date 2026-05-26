from pathlib import Path

from litestar import Litestar, get
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get("/uploads")
async def get_uploads() -> Template:
    return Template(
        template_str="<p>debug={{ debug }}</p>",
        context={"debug": True},
    )


app = Litestar(
    route_handlers=[get_uploads],
    template_config=TemplateConfig(
        directory=Path(__file__).parent,
        engine=JinjaTemplateEngine,
    ),
)
