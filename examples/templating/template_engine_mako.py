from pathlib import Path

from starlite import Starlite, TemplateConfig
from starlite.contrib.mako import MakoTemplateEngine

app = Starlite(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MakoTemplateEngine,
    ),
)
