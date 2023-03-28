from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.template.config import TemplateConfig

template_config = TemplateConfig(engine=JinjaTemplateEngine)
template_config.engine_instance.engine.globals["foo"] = "bar"
