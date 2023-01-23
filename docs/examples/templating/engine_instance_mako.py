from starlite import TemplateConfig
from starlite.contrib.mako import MakoTemplateEngine

template_config = TemplateConfig(engine=MakoTemplateEngine)
template_config.engine_instance.engine.has_template("foo")
