from litestar.contrib.mako import MakoTemplateEngine
from litestar.template.config import TemplateConfig

template_config = TemplateConfig(engine=MakoTemplateEngine, directory="templates")
