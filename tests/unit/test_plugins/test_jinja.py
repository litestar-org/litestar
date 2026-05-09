from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from jinja2 import Environment

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.jinja import JinjaTemplateEngine

if TYPE_CHECKING:
    from pathlib import Path


def test_jinja_template_engine_instantiation_error(tmp_path: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        JinjaTemplateEngine(directory=tmp_path, engine_instance=Environment())


def test_jinja_template_engine_instantiated_with_directory(tmp_path: Path) -> None:
    engine = JinjaTemplateEngine(directory=tmp_path)
    assert isinstance(engine.engine, Environment)


def test_jinja_template_engine_instantiated_with_engine() -> None:
    env = Environment()
    engine = JinjaTemplateEngine(engine_instance=env)
    assert engine.engine is env


def test_jinja_template_engine_from_environment() -> None:
    env = Environment()
    engine = JinjaTemplateEngine.from_environment(env)
    assert engine.engine is env


def test_jinja_render_string() -> None:
    engine = JinjaTemplateEngine(engine_instance=Environment())
    out = engine.render_string("hello {{ name }}", {"name": "world"})
    assert out == "hello world"


def test_jinja_get_template_raises_template_not_found(tmp_path: Path) -> None:
    engine = JinjaTemplateEngine(directory=tmp_path)
    with pytest.raises(TemplateNotFoundException):
        engine.get_template("missing.html")


def test_jinja_get_template_returns_template(tmp_path: Path) -> None:
    (tmp_path / "hi.html").write_text("hi {{ name }}")
    engine = JinjaTemplateEngine(directory=tmp_path)
    template = engine.get_template("hi.html")
    assert template.render(name="xyz") == "hi xyz"


def test_jinja_register_template_callable() -> None:
    engine = JinjaTemplateEngine(engine_instance=Environment())

    def shouter(context: object, value: str) -> str:
        return value.upper()

    engine.register_template_callable(key="shout", template_callable=shouter)
    rendered = engine.render_string("{{ shout('hi') }}", {})
    assert rendered == "HI"
