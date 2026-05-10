"""Functional tests for litestar.plugins.mako."""

from pathlib import Path

import pytest
from mako.lookup import TemplateLookup  # type: ignore[import-untyped]

from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException
from litestar.plugins.mako import MakoTemplate, MakoTemplateEngine


def test_init_with_directory(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.mako").write_text("Hello ${name}!")

    engine = MakoTemplateEngine(directory=template_dir)
    assert isinstance(engine.engine, TemplateLookup)


def test_init_with_directory_list(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    engine = MakoTemplateEngine(directory=[first, second])
    assert isinstance(engine.engine, TemplateLookup)


def test_init_with_engine_instance(tmp_path: Path) -> None:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    engine = MakoTemplateEngine(engine_instance=lookup)
    assert engine.engine is lookup


def test_init_raises_when_both_directory_and_engine_instance(tmp_path: Path) -> None:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    with pytest.raises(ImproperlyConfiguredException):
        MakoTemplateEngine(directory=tmp_path, engine_instance=lookup)


def test_from_template_lookup_classmethod(tmp_path: Path) -> None:
    lookup = TemplateLookup(directories=[str(tmp_path)])
    engine = MakoTemplateEngine.from_template_lookup(lookup)
    assert isinstance(engine, MakoTemplateEngine)
    assert engine.engine is lookup


def test_get_template_returns_template(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.mako").write_text("Hello ${name}!")

    engine = MakoTemplateEngine(directory=template_dir)
    template = engine.get_template("hello.mako")
    assert isinstance(template, MakoTemplate)
    assert template.render(name="World") == "Hello World!"


def test_get_template_raises_when_missing(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    engine = MakoTemplateEngine(directory=template_dir)
    with pytest.raises(TemplateNotFoundException):
        engine.get_template("missing.mako")


def test_render_string() -> None:
    engine = MakoTemplateEngine(directory=Path("."))
    rendered = engine.render_string("Hello ${name}!", {"name": "World"})
    assert rendered == "Hello World!"


def test_register_template_callable_appends() -> None:
    engine = MakoTemplateEngine(directory=Path("."))

    def shout(_context: object, value: str) -> str:
        return value.upper()

    engine.register_template_callable(key="shout", template_callable=shout)
    assert any(key == "shout" for key, _ in engine._template_callables)


def test_csrf_token_and_url_for_registered_by_default() -> None:
    engine = MakoTemplateEngine(directory=Path("."))
    keys = {key for key, _ in engine._template_callables}
    assert "csrf_token" in keys
    assert "url_for" in keys


def test_template_render_invokes_callables(tmp_path: Path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "hello.mako").write_text("${shout(name)}")

    engine = MakoTemplateEngine(directory=template_dir)

    def shout(_context: object, value: str) -> str:
        return value.upper()

    engine.register_template_callable(key="shout", template_callable=shout)
    template = engine.get_template("hello.mako")
    assert template.render(name="world") == "WORLD"
