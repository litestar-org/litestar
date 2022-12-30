from pathlib import Path

from starlite import Request, Starlite, Template, TemplateConfig, get
from starlite.contrib.mako import MakoTemplateEngine


@get(path="/")
def index(request: Request) -> Template:
    return Template(name="index.html", context={"user": request.user})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MakoTemplateEngine,
    ),
)
