from starlite.contrib.mako import MakoTemplateEngine
from starlite import Request, Template, get
from starlite import Starlite, TemplateConfig


@get(path="/")
def index(request: Request) -> Template:
    return Template(name="index.html", context={"user": request.user})


app = Starlite(
    route_handlers=[index],
    template_config=TemplateConfig(directory="templates", engine=MakoTemplateEngine),
)
