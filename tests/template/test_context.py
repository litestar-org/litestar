from pathlib import Path
from typing import Any

import pytest

from starlite import MediaType, get
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.contrib.mako import MakoTemplateEngine
from starlite.response_containers import Template
from starlite.template.config import TemplateConfig
from starlite.testing import create_test_client


@pytest.mark.parametrize(
    "engine, template, expected",
    (
        (JinjaTemplateEngine, 'path: {{ request.scope["path"] }}', "path: /"),
        (MakoTemplateEngine, 'path: ${request.scope["path"]}', "path: /"),
    ),
)
def test_request_is_set_in_context(engine: Any, template: str, expected: str, template_dir: Path) -> None:
    Path(template_dir / "abc.html").write_text(template)

    @get(path="/", media_type=MediaType.HTML)
    def handler() -> Template:
        return Template(name="abc.html", context={"request": {"scope": {"path": "nope"}}})

    with create_test_client(
        route_handlers=[handler],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=engine,
        ),
    ) as client:
        response = client.get("/")
        assert response.text == expected
