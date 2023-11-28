from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from minijinja import Environment  # type: ignore[import-untyped]

from litestar.contrib.minijinja import MiniJinjaTemplateEngine
from litestar.exceptions import ImproperlyConfiguredException, TemplateNotFoundException

if TYPE_CHECKING:
    from pathlib import Path


def test_mini_jinja_template_engine_instantiation_error(tmp_path: Path) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine(directory=tmp_path, engine_instance=Environment())

    with pytest.raises(ImproperlyConfiguredException):
        MiniJinjaTemplateEngine()


def test_mini_jinja_template_engine_instantiated_with_engine() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine(engine_instance=engine)
    assert template_engine.engine is engine


def test_mini_jinja_template_render_raises_template_not_found(tmp_path: Path) -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())
    with pytest.raises(TemplateNotFoundException):
        tmpl = template_engine.get_template("not_found.html")
        tmpl.render()


def test_mini_jinja_template_render_string(tmp_path: Path) -> None:
    template_engine = MiniJinjaTemplateEngine(engine_instance=Environment())

    good_template = template_engine.render_string("template as a {{value}}", context={"value": "string"})
    assert good_template == "template as a string"


def test_from_environment() -> None:
    engine = Environment()
    template_engine = MiniJinjaTemplateEngine.from_environment(engine)
    assert template_engine.engine is engine
