from starlite.contrib.mako import MakoTemplateEngine
from starlite.template.config import TemplateConfig

template_config = TemplateConfig(engine=MakoTemplateEngine)
template_config.engine_instance.engine.has_template("foo")
