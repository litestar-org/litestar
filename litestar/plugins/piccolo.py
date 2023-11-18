from __future__ import annotations

from litestar.exceptions import MissingDependencyException

try:
    from litestar_piccolo import PiccoloDTO, PiccoloPlugin, PiccoloSerializationPlugin
except ImportError as e:
    raise MissingDependencyException("litestar-piccolo") from e


__all__ = ("PiccoloDTO", "PiccoloSerializationPlugin", "PiccoloPlugin")
