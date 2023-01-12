from typing import TYPE_CHECKING

from starlite import TemplateConfig
from starlite.contrib.jinja import JinjaTemplateEngine

if TYPE_CHECKING:
    from pathlib import Path


def test_pytest_config_caches_engine_instance(template_dir: "Path") -> None:
    config = TemplateConfig(
        directory=template_dir,
        engine=JinjaTemplateEngine,
    )
    assert config.engine_instance is config.engine_instance
