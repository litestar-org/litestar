from pathlib import Path

from starlite import Request, Starlite, Template, TemplateConfig, get
from starlite.contrib.jinja import JinjaTemplateEngine


@get(path="/")
def index(request: Request) -> Template:
    return Template(name="info.html", context={"user": request.user})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
)
