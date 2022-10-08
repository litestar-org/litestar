from pathlib import Path

from starlite import MediaType, Template, TemplateConfig, get
from starlite.template.jinja import JinjaTemplateEngine
from starlite.testing import create_test_client


def test_request_is_set_in_context(template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text('path: {{ request.scope["path"] }}')

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html", context={"request": {"scope": {"path": "nope"}}})

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
    ) as client:
        response = client.get("/")
        assert response.text == "path: /"
