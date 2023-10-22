from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get(path="/")
def index(name: str) -> Template:
    return Template(template_name="hello.html.minijinja", context={"name": name})


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path(__file__).parent / "templates",
        engine=MiniJinjaTemplateEngine,
    ),
)
