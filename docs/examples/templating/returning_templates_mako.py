from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.mako import MakoTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get(path="/{template_type: str}", sync_to_thread=False)
def index(name: str, template_type: str) -> Template:
    if template_type == "file":
        return Template(template_name="hello.html.mako", context={"name": name})
    elif template_type == "string":
        return Template(template_str="Hello <strong>Mako</strong> using strings", context={"name": name})


app = Litestar(
    route_handlers=[index],
    template_config=TemplateConfig(
        directory=Path(__file__).parent / "templates",
        engine=MakoTemplateEngine,
    ),
)
