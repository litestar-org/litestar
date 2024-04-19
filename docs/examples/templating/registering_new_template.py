from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template import TemplateConfig
from jinja2 import Environment, DictLoader

my_custom_env = Environment(loader=DictLoader({"index.html": "Hello {{name}}!"}))
app = Litestar(
    template_config=TemplateConfig(
        instance=JinjaTemplateEngine.from_environment(my_custom_env)
    )
)