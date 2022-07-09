from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from starlite.config import TemplateConfig
    from starlite.template import TemplateEngineProtocol


def create_template_engine(template_config: TemplateConfig | None) -> TemplateEngineProtocol | None:
    """
    Construct a template engine if `template_config` is provided.

    Parameters
    ----------
    template_config : TemplateConfig | None

    Returns
    -------
    TemplateEngineProtocol | None
    """
    template_engine: TemplateEngineProtocol | None
    if template_config:
        template_engine = template_config.engine(template_config.directory)
        if template_config.engine_callback is not None:
            template_config.engine_callback(template_engine)
    else:
        template_engine = None
    return template_engine
