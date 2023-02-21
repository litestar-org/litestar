from pathlib import Path

from starlite import Starlite, get
from starlite.config.template import TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.response_containers import Template


@get(path="/")
def index(name: str) -> Template:
    return Template(name="hello.html.jinja2", context={"name": name})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
)
