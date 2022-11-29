from typing import Dict
from starlite import TemplateConfig, Starlite, get, Template
from starlite.template.jinja import JinjaTemplateEngine
from pathlib import Path

template_path = Path(__file__).parent / "templates"
template_config = TemplateConfig(directory=template_path, engine=JinjaTemplateEngine)


@get("/")
def index() -> Template:
    return Template(name="index.html.jinja2")


def my_template_function(ctx: Dict) -> str:
    return ctx.get("my_context_key", "nope")


template_config.engine.register_template_callable(
    key="check_context_key", template_callable=my_template_function
)

app = Starlite(
    route_handlers=[index],
    template_config=template_config,
)