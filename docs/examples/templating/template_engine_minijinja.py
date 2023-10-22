from pathlib import Path

from litestar import Litestar
from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.template.config import TemplateConfig

app = Litestar(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MiniJinjaTemplateEngine,
    ),
)
