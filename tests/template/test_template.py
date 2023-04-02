import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Type, Union

import pytest

from starlite import MediaType, Starlite, get
from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.contrib.mako import MakoTemplateEngine
from starlite.exceptions import ImproperlyConfiguredException
from starlite.response_containers import Template
from starlite.template.config import TemplateConfig
from starlite.testing import create_test_client

if TYPE_CHECKING:
    from starlite import Request
    from starlite.template import TemplateEngineProtocol


def test_handler_raise_for_no_template_engine() -> None:
    @get(path="/")
    def invalid_path() -> Template:
        return Template(name="index.html", context={"ye": "yeeee"})

    with create_test_client(route_handlers=[invalid_path]) as client:
        response = client.request("GET", "/")
        assert response.status_code == 500
        assert response.json() == {"detail": "Template engine is not configured", "status_code": 500}


def test_engine_passed_to_callback(template_dir: "Path") -> None:
    received_engine: Optional[JinjaTemplateEngine] = None

    def callback(engine: JinjaTemplateEngine) -> None:
        nonlocal received_engine
        received_engine = engine

    app = Starlite(
        route_handlers=[],
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
            engine_callback=callback,
        ),
    )

    assert received_engine is not None
    assert received_engine is app.template_engine


@pytest.mark.parametrize("engine", (JinjaTemplateEngine, MakoTemplateEngine))
def test_engine_instance(engine: Type["TemplateEngineProtocol"], template_dir: "Path") -> None:
    engine_instance = engine(template_dir)
    config = TemplateConfig(engine=engine_instance)
    assert config.engine_instance is engine_instance


@pytest.mark.parametrize("engine", (JinjaTemplateEngine, MakoTemplateEngine))
def test_directory_validation(engine: Type["TemplateEngineProtocol"], template_dir: "Path") -> None:
    with pytest.raises(ImproperlyConfiguredException):
        TemplateConfig(engine=engine)


@pytest.mark.parametrize("media_type", [MediaType.HTML, MediaType.TEXT, "text/arbitrary"])
def test_media_type(media_type: Union[MediaType, str], template_dir: Path) -> None:
    (template_dir / "hello.tpl").write_text("hello")

    @get("/", media_type=media_type)
    def index() -> Template:
        return Template(name="hello.tpl")

    with create_test_client(
        [index], template_config=TemplateConfig(directory=template_dir, engine=JinjaTemplateEngine)
    ) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith(
            media_type if isinstance(media_type, str) else media_type.value,  # type: ignore[union-attr]
        )


@pytest.mark.parametrize(
    "extension,expected_type",
    [
        (".html", MediaType.HTML),
        (".html.other", MediaType.HTML),
        (".xml", MediaType.XML),
        (".xml.other", MediaType.XML),
        (".txt", MediaType.TEXT),
        (".unknown", MediaType.TEXT),
        ("", MediaType.TEXT),
    ],
)
@pytest.mark.skipif(sys.platform == "win32", reason="mimetypes.guess_types is unreliable on windows")
def test_media_type_inferred(extension: str, expected_type: MediaType, template_dir: Path) -> None:
    tpl_name = "hello" + extension
    (template_dir / tpl_name).write_text("hello")

    @get("/")
    def index() -> Template:
        return Template(name=tpl_name)

    with create_test_client(
        [index], template_config=TemplateConfig(directory=template_dir, engine=JinjaTemplateEngine)
    ) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith(expected_type.value)


def test_before_request_handler_content_type(template_dir: Path) -> None:
    (template_dir / "about.html").write_text("about starlite...")

    def before_request_handler(request: "Request") -> None:
        return None

    @get("/", before_request=before_request_handler)
    def index() -> Template:
        return Template(name="about.html")

    with create_test_client(
        [index], template_config=TemplateConfig(directory=template_dir, engine=JinjaTemplateEngine)
    ) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith(MediaType.HTML.value)
