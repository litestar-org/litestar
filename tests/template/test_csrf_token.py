from pathlib import Path

from starlite import CSRFConfig, MediaType, Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.template.mako import MakoTemplateEngine
from starlite.testing import create_test_client
from starlite.utils import generate_csrf_token


def test_jinja_csrf_token(template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text("{{ csrf_token() }}")

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
        csrf_config=csrf_config,
    ) as client:
        response = client.get("/")
        assert len(response.text) == len(generate_csrf_token(csrf_config.secret))


def test_mako_csrf_token(template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text("${csrf_token()}")

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html")

    csrf_config = CSRFConfig(secret="yaba daba do")

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=MakoTemplateEngine,
        ),
        csrf_config=csrf_config,
    ) as client:
        response = client.get("/")
        assert len(response.text) == len(generate_csrf_token(csrf_config.secret))
