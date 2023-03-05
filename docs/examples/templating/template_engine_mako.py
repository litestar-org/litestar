from pathlib import Path

from starlite import Starlite
from starlite.contrib.mako import MakoTemplateEngine
from starlite.template.config import TemplateConfig

app = Starlite(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MakoTemplateEngine,
    ),
)
