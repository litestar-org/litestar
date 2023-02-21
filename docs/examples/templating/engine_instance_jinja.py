from starlite.config.template import TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine

template_config = TemplateConfig(engine=JinjaTemplateEngine)
template_config.engine_instance.engine.globals["foo"] = "bar"
