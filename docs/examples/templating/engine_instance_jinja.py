from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

template_config = TemplateConfig(engine=JinjaTemplateEngine, directory="templates")
