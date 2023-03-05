from pathlib import Path

from starlite import Starlite
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.template.config import TemplateConfig

app = Starlite(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=JinjaTemplateEngine,
    ),
)
