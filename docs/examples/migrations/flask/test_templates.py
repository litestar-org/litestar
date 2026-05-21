from litestar import Litestar, get
from litestar.params import FromPath
from litestar.plugins.jinja import JinjaTemplateEngine
from litestar.response import Template
from litestar.template.config import TemplateConfig


@get("/hello/{name:str}", sync_to_thread=False)
def hello(name: FromPath[str]) -> Template:
    return Template(template_name="hello.html", context={"name": name})


app = Litestar(
    [hello],
    template_config=TemplateConfig(directory="templates", engine=JinjaTemplateEngine),
)

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


@pytest.fixture
def templates_cwd(tmp_path: Path) -> Iterator[Path]:
    (tmp_path / "templates").mkdir()
    (tmp_path / "templates" / "hello.html").write_text("Hello, {{ name }}!")
    previous = Path.cwd()
    os.chdir(tmp_path)
    try:
        yield tmp_path
    finally:
        os.chdir(previous)


def test_renders_template(templates_cwd: Path) -> None:
    assert (templates_cwd / "templates" / "hello.html").is_file()
    with TestClient(app) as client:
        response = client.get("/hello/julien")
        assert response.status_code == HTTP_200_OK
        assert response.text == "Hello, julien!"
