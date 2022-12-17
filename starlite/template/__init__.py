from typing import Any
from warnings import warn

from .base import TemplateEngineProtocol, TemplateProtocol

__all__ = ("TemplateEngineProtocol", "TemplateProtocol")


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

    warn(
        f"Importing {name} from {__package__} is deprecated, use `from startlite.contrib.{module} import {name}` instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    globals()[name] = export
    return export
