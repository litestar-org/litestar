from pathlib import Path

from starlite import Starlite, Template, TemplateConfig, get
from starlite.contrib.mako import MakoTemplateEngine


@get(path="/")
def index(name: str) -> Template:
    return Template(name="hello.html.mako", context={"name": name})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MakoTemplateEngine,
    ),
)
