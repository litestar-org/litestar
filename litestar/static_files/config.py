from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem
from litestar.handlers import asgi
from litestar.static_files.base import StaticFiles
from litestar.utils import normalize_path

__all__ = ("StaticFilesConfig",)


if TYPE_CHECKING:
    from litestar.handlers.asgi_handlers import ASGIRouteHandler
    from litestar.types import ExceptionHandlersMap, Guard, PathType


@dataclass
class StaticFilesConfig:
    """Configuration for static file service.

    To enable static files, pass an instance of this class to the :class:`Litestar <litestar.app.Litestar>` constructor using
    the 'static_files_config' key.
    """

    path: str
    """Path to serve static files from.

    Note that the path cannot contain path parameters.
    """
    directories: list[PathType]
    """A list of directories to serve files from."""
    html_mode: bool = False
    """Flag dictating whether serving html.

    If true, the default file will be 'index.html'.
    """
    name: str | None = None
    """An optional string identifying the static files handler."""
    file_system: Any = BaseLocalFileSystem()  # noqa: RUF009
    """The file_system spec to use for serving files.

    Notes:
        - A file_system is a class that adheres to the
            :class:`FileSystemProtocol <litestar.types.FileSystemProtocol>`.
        - You can use any of the file systems exported from the
            [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library for this purpose.
    """
    opt: dict[str, Any] | None = None
    """A string key dictionary of arbitrary values that will be added to the static files handler."""
    guards: list[Guard] | None = None
    """A list of :class:`Guard <litestar.types.Guard>` callables."""
    exception_handlers: ExceptionHandlersMap | None = None
    """A dictionary that maps handler functions to status codes and/or exception types."""
    send_as_attachment: bool = False
    """Whether to send the file as an attachment."""

    def __post_init__(self) -> None:
        if not self.path:
            raise ImproperlyConfiguredException("path must be a non-zero length string,")

        if not self.directories or not any(bool(d) for d in self.directories):
            raise ImproperlyConfiguredException("directories must include at least one path.")

        if "{" in self.path:
            raise ImproperlyConfiguredException("path parameters are not supported for static files")

        if not (
            callable(getattr(self.file_system, "info", None)) and callable(getattr(self.file_system, "open", None))
        ):
            raise ImproperlyConfiguredException("file_system must adhere to the FileSystemProtocol type")

        self.path = normalize_path(self.path)

    def to_static_files_app(self) -> ASGIRouteHandler:
        """Return an ASGI app serving static files based on the config.

        Returns:
            :class:`StaticFiles <litestar.static_files.StaticFiles>`
        """
        static_files = StaticFiles(
            is_html_mode=self.html_mode,
            directories=self.directories,
            file_system=self.file_system,
            send_as_attachment=self.send_as_attachment,
        )
        return asgi(
            path=self.path,
            name=self.name,
            is_static=True,
            opt=self.opt,
            guards=self.guards,
            exception_handlers=self.exception_handlers,
        )(static_files)
