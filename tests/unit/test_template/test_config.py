from typing import TYPE_CHECKING

from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.template.config import TemplateConfig

if TYPE_CHECKING:
    from pathlib import Path


def test_pytest_config_caches_engine_instance(tmp_path: "Path") -> None:
    config = TemplateConfig(
        directory=tmp_path,
        engine=JinjaTemplateEngine,
    )
    assert config.engine_instance is config.engine_instance
