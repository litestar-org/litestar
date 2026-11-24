import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from litestar.di._helpers import _format_key
from litestar.di.exceptions import DIRegistrationError
from litestar.exceptions import DTOFactoryException, ImproperlyConfiguredException

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Self

    from litestar.di.provider import DependencyKey
    from litestar.handlers import BaseRouteHandler

__all__ = ("HandlerErrorPrefix",)


@dataclass
class HandlerErrorPrefix:
    handler: str
    paths: list[str]
    dependencies: "tuple[DependencyKey, ...]" = ()

    @classmethod
    def for_handler(cls, handler: "BaseRouteHandler") -> "Self":
        """Return the prefix naming ``handler`` by its ``name`` option, or its function's name, and its paths."""
        return cls(handler=handler.name or handler.handler_name, paths=sorted(handler.paths))

    def format(self, msg: str | None = None) -> str:
        paths = ",".join(sorted(self.paths))
        out = f"[paths={paths!r}, handler={self.handler!r}"
        if self.dependencies:
            out += f", dependencies={' -> '.join(_format_key(key) for key in reversed(self.dependencies))}"
        out += "]"
        if msg:
            out = f"{out} {msg}"
        return out

    @contextlib.contextmanager
    def wrap_config_exception(self) -> "Generator[None]":
        try:
            yield
        except ImproperlyConfiguredException as exc:
            new_msg = self.format(exc.detail)
            raise ImproperlyConfiguredException(new_msg) from exc
        except DIRegistrationError as exc:
            raise DIRegistrationError(self.format(str(exc))) from exc

    @contextlib.contextmanager
    def wrap_dto_exception(self) -> "Generator[None]":
        """Prefix the message of a :class:`~litestar.exceptions.DTOFactoryException` raised in the block and re-raise
        the same exception, keeping its class, attributes and traceback.
        """
        try:
            yield
        except DTOFactoryException as exc:
            detail = exc.detail
            if not detail:
                exc.detail = self.format()
                raise
            prefixed = self.format(detail)
            exc.detail = prefixed
            exc.args = tuple(arg.replace(detail, prefixed, 1) if isinstance(arg, str) else arg for arg in exc.args)
            raise
