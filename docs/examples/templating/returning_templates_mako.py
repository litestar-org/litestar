from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.mako import MakoTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get(path="/", sync_to_thread=False)
def index(name: str) -> Template:
    return Template(template_name="hello.html.mako", context={"name": name})


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path(__file__).parent / "templates",
        engine=MakoTemplateEngine,
    ),
)
