from pathlib import Path
from typing import Dict

from starlite import Starlite, get
from starlite.contrib.mako import MakoTemplateEngine
from starlite.response_containers import Template
from starlite.template.config import TemplateConfig


def my_template_function(ctx: Dict) -> str:
    return ctx.get("my_context_key", "nope")


def register_template_callables(engine: MakoTemplateEngine) -> None:
    engine.register_template_callable(
        key="check_context_key",
        template_callable=my_template_function,
    )


template_config = TemplateConfig(
    directory=Path("templates"),
    engine=MakoTemplateEngine,
    engine_callback=register_template_callables,
)


@get("/")
def index() -> Template:
    return Template(name="index.html.mako")


app = Starlite(
    route_handlers=[index],
    template_config=template_config,
)
