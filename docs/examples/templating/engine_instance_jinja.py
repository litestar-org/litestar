from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

template_config = TemplateConfig(engine=JinjaTemplateEngine)
template_config.engine_instance.engine.globals["foo"] = "bar"
