from jinja2.environment import Environment
from jinja2.loaders import DictLoader

from litestar import Litestar, get
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template import TemplateConfig

jinja_env = Environment(enable_async=True, loader=DictLoader({"index.html": "Hello {{name}}!"}))
template_config = TemplateConfig(instance=JinjaTemplateEngine.from_environment(jinja_env))


@get("/")
async def index() -> Template:
    return Template("index.html", context={"name": "Litestar"})


app = Litestar(route_handlers=[index], template_config=template_config)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
