from docs.examples.templating.engine_instance_jinja import template_config as template_config_jinja
from docs.examples.templating.engine_instance_mako import template_config as template_config_mako
from docs.examples.templating.engine_instance_minijinja import template_config as template_config_minijinja
from jinja2 import Environment as JinjaEnvironment
from mako.lookup import TemplateLookup
from minijinja import Environment as MiniJinjaEnvoronment


def test_engine_instance_jinja() -> None:
    assert isinstance(template_config_jinja.engine_instance.engine, JinjaEnvironment)


def test_engine_instance_mako() -> None:
    assert isinstance(template_config_mako.engine_instance.engine, TemplateLookup)


def test_engine_instance_minijinja() -> None:
    assert isinstance(template_config_minijinja.engine_instance.engine, MiniJinjaEnvoronment)
