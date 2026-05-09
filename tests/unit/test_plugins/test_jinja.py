"""Functional tests for litestar.plugins.jinja."""

from pathlib import Path

import pytest
from jinja2 import DictLoader, Environment

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.jinja import JinjaTemplateEngine


def test_init_with_directory(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.html").write_text("Hello {{ name }}!")

    engine = JinjaTemplateEngine(directory=template_dir)
    assert isinstance(engine.engine, Environment)


def test_init_with_directory_list(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    engine = JinjaTemplateEngine(directory=[first, second])
    assert isinstance(engine.engine, Environment)


def test_init_with_engine_instance() -> None:
    env = Environment(loader=DictLoader({"hello.html": "Hi {{ name }}"}), autoescape=True)
    engine = JinjaTemplateEngine(engine_instance=env)
    assert engine.engine is env


def test_init_raises_when_both_directory_and_engine_instance(tmp_path: Path) -> None:
    env = Environment(loader=DictLoader({}))
    with pytest.raises(ImproperlyConfiguredException):
        JinjaTemplateEngine(directory=tmp_path, engine_instance=env)


def test_from_environment_classmethod() -> None:
    env = Environment(loader=DictLoader({}), autoescape=True)
    engine = JinjaTemplateEngine.from_environment(env)
    assert isinstance(engine, JinjaTemplateEngine)
    assert engine.engine is env


def test_get_template_returns_template(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.html").write_text("Hello {{ name }}!")

    engine = JinjaTemplateEngine(directory=template_dir)
    template = engine.get_template("hello.html")
    assert template.render({"name": "World"}) == "Hello World!"


def test_get_template_raises_when_missing(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    engine = JinjaTemplateEngine(directory=template_dir)
    with pytest.raises(TemplateNotFoundException):
        engine.get_template("missing.html")


def test_render_string() -> None:
    env = Environment(loader=DictLoader({}), autoescape=True)
    engine = JinjaTemplateEngine(engine_instance=env)
    rendered = engine.render_string("Hello {{ name }}!", {"name": "World"})
    assert rendered == "Hello World!"


def test_register_template_callable_adds_to_globals() -> None:
    env = Environment(loader=DictLoader({}), autoescape=True)
    engine = JinjaTemplateEngine(engine_instance=env)

    def shout(_context: object, value: str) -> str:
        return value.upper()

    engine.register_template_callable(key="shout", template_callable=shout)
    assert "shout" in engine.engine.globals


def test_csrf_token_and_url_for_registered_by_default(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    engine = JinjaTemplateEngine(directory=template_dir)
    assert "csrf_token" in engine.engine.globals
    assert "url_for" in engine.engine.globals
