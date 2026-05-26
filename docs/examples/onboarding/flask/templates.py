from pathlib import Path

from litestar import Litestar, get
from litestar.params import FromPath
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get("/hello/{name:str}", sync_to_thread=False)
def hello(name: FromPath[str]) -> Template:
    return Template(
        template_str="<p>Hello, {{ name }}!</p>",
        context={"name": name},
    )


app = Litestar(
    route_handlers=[hello],
    template_config=TemplateConfig(
        directory=Path(__file__).parent,
        engine=JinjaTemplateEngine,
    ),
)
