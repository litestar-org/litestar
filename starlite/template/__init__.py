from typing import Any

from .base import TemplateEngineProtocol, TemplateProtocol

__all__ = ("TemplateEngineProtocol", "TemplateProtocol")

from ..utils import warn_deprecation


def __getattr__(name: str) -> Any:
    """Provide lazy importing as per https://peps.python.org/pep-0562/"""

    if name not in {"JinjaTemplateEngine", "MakoTemplateEngine", "MakoTemplate"}:
        raise AttributeError(f"Module {__package__} has no attribute {name}")

    if name == "JinjaTemplateEngine":
        from starlite.contrib.jinja import JinjaTemplateEngine

        export: Any = JinjaTemplateEngine
        module = "jinja"
    elif name == "MakoTemplateEngine":
        from starlite.contrib.mako import MakoTemplateEngine

        export = MakoTemplateEngine
        module = "mako"
    else:
        from starlite.contrib.mako import MakoTemplate

        export = MakoTemplate
        module = "mako"

    warn_deprecation(
        deprecated_name=f"{name} from {__package__}",
        kind="import",
        alternative=f"'from startlite.contrib.{module} import {name}'",
        version="1.46.0",
    )

    globals()[name] = export
    return export
