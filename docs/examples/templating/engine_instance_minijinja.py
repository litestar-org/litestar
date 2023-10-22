from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.template.config import TemplateConfig

template_config = TemplateConfig(engine=MiniJinjaTemplateEngine, directory="templates")
