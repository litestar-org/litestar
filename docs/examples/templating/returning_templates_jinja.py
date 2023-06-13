from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import TemplateResponse
from litestar.template.config import TemplateConfig


@get(path="/")
def index(name: str) -> TemplateResponse:
    return TemplateResponse(template_name="hello.html.jinja2", context={"name": name})


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
)
