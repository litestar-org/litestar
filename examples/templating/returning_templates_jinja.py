from starlite import Request, Template, get
from starlite import Starlite, TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine


@get(path="/")
def index(request: Request) -> Template:
    return Template(name="info.html", context={"user": request.user})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
)
