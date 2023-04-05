from typing import TYPE_CHECKING

from starlite.contrib.jinja import JinjaTemplateEngine
from starlite.template.config import TemplateConfig

if TYPE_CHECKING:
    from pathlib import Path


def test_pytest_config_caches_engine_instance(template_dir: "Path") -> None:
    config = TemplateConfig(
        directory=template_dir,
        engine=JinjaTemplateEngine,
    )
    assert config.engine_instance is config.engine_instance
