from starlite import Starlite, TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine


app = Starlite(
    route_handlers=[...],
    template_config=TemplateConfig(
        directory="templates",  # (1)!
        engine=JinjaTemplateEngine,
    ),
)
