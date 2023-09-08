from pathlib import Path

from litestar import Litestar
from litestar.contrib.minijnja import MiniJinjaTemplateEngine
from litestar.template.config import TemplateConfig

app = Litestar(
    route_handlers=[],
    template_config=TemplateConfig(
        directory=Path("templates"),
        engine=MiniJinjaTemplateEngine,
    ),
)
