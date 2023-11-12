from pathlib import Path

from litestar import Litestar, get
from litestar.contrib.minijinja import MiniJinjaTemplateEngine, StateProtocol
from litestar.response import Template
from litestar.template.config import TemplateConfig


def my_template_function(ctx: StateProtocol) -> str:
    return ctx.lookup("my_context_key") or "nope"


def register_template_callables(engine: MiniJinjaTemplateEngine) -> None:
    engine.register_template_callable(key="check_context_key", template_callable=my_template_function)


template_config = TemplateConfig(
    directory=Path(__file__).parent / "templates",
    engine=MiniJinjaTemplateEngine,
    engine_callback=register_template_callables,
)


@get("/", sync_to_thread=False)
def index() -> Template:
    return Template(template_name="index.html.minijinja")


app = Litestar(route_handlers=[index], template_config=template_config)
