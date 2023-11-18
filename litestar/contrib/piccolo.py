from __future__ import annotations

from litestar.exceptions import MissingDependencyException

try:
    from litestar_piccolo import PiccoloDTO
except ImportError as e:
    raise MissingDependencyException("litestar-piccolo") from e


from litestar.utils import warn_deprecation

__all__ = ("PiccoloDTO",)


warn_deprecation(
    deprecated_name="litestar.contrib.piccolo",
    version="2.3.2",
    kind="import",
    removal_in="3.0",
    info="importing from 'litestar.contrib.piccolo' is deprecated, please import from 'litestar_piccolo' instead",
)
