"""Functional tests for litestar.plugins.minijinja."""

from pathlib import Path

import pytest
from minijinja import Environment

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.minijinja import MiniJinjaTemplateEngine, _transform_state


def test_minijinja_template_engine_instantiation_error(tmp_path: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine(directory=tmp_path, engine_instance=Environment())

    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine()


def test_minijinja_template_engine_instantiated_with_engine() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine(engine_instance=engine)
    assert template_engine.engine is engine


def test_minijinja_template_engine_instantiated_with_directory(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.html").write_text("Hello {{ name }}!")

    template_engine = MiniJinjaTemplateEngine(directory=template_dir)
    assert isinstance(template_engine.engine, Environment)


def test_minijinja_template_engine_instantiated_with_directory_list(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (second / "hello.html").write_text("Hi {{ name }}!")

    template_engine = MiniJinjaTemplateEngine(directory=[first, second])
    template = template_engine.get_template("hello.html")
    assert template.render(name="World") == "Hi World!"


def test_minijinja_template_render_raises_template_not_found(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_engine = MiniJinjaTemplateEngine(directory=template_dir)
    with pytest.raises(TemplateNotFoundException):
        tmpl = template_engine.get_template("not_found.html")
        tmpl.render()


def test_minijinja_template_render_string() -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())
    rendered = template_engine.render_string("template as a {{ value }}", context={"value": "string"})
    assert rendered == "template as a string"


def test_minijinja_from_environment() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine.from_environment(engine)
    assert template_engine.engine is engine


def test_transform_state_callable_invoked_with_template_context() -> None:
    captured: dict[str, object] = {}

    def callable_taking_context(context: object, value: str) -> str:
        captured["context"] = context
        return value.upper()

    wrapped = _transform_state(callable_taking_context)
    engine = Environment()
    engine.add_global("shout", wrapped)
    rendered = engine.render_str("{{ shout('hi') }}")
    assert rendered == "HI"
    assert "context" in captured


def test_register_template_callable_wraps_undecorated_callable() -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())

    def shout(_context: object, value: str) -> str:
        return value.upper()

    template_engine.register_template_callable("shout", shout)
    rendered = template_engine.render_string("{{ shout('hi') }}", context={})
    assert rendered == "HI"
