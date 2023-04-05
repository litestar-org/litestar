from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.mako import MakoTemplateEngine
from litestar.response_containers import Template
from litestar.template.config import TemplateConfig


@get(path="/")
def index(name: str) -> Template:
    return Template(name="hello.html.mako", context={"name": name})


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MakoTemplateEngine,
    ),
)
