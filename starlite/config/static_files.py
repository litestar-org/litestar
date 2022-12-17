from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseConfig, BaseModel, DirectoryPath, constr, validator

from starlite.handlers import asgi
from starlite.static_files.base import StaticFiles
from starlite.types import ExceptionHandlersMap, Guard
from starlite.utils import normalize_path
from starlite.utils.file import BaseLocalFileSystem

if TYPE_CHECKING:
    from starlite.handlers import ASGIRouteHandler
    from starlite.types.file_types import FileSystemProtocol


class StaticFilesConfig(BaseModel):
    """Configuration for static file service.

    To enable static files, pass an instance of this class to the [Starlite][starlite.app.Starlite] constructor using
    the 'static_files_config' key.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    path: constr(min_length=1)  # type: ignore
    """Path to serve static files from.

    Note that the path cannot contain path parameters.
    """
    directories: List[DirectoryPath]
    """A list of directories to serve files from."""
    html_mode: bool = False
    """Flag dictating whether serving html.

    If true, the default file will be 'index.html'.
    """
    name: Optional[str] = None
    """An optional string identifying the static files handler."""
    file_system: Any = BaseLocalFileSystem()
    """The file_system spec to use for serving files.

    Notes:
        - A file_system is a class that adheres to the
            [FileSystemProtocol][starlite.types.FileSystemProtocol].
        - You can use any of the file systems exported from the
            [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) library for this purpose.
    """
    opt: Optional[Dict[str, Any]] = None
    """A string key dictionary of arbitrary values that will be added to the static files handler."""
    guards: Optional[List[Guard]] = None
    """A list of [Guard][starlite.types.Guard] callables."""
    exception_handlers: Optional[ExceptionHandlersMap] = None
    """A dictionary that maps handler functions to status codes and/or exception types."""
    send_as_attachment: bool = False
    """Whether to send the file as an attachment."""

    @validator("path", always=True)
    def validate_path(cls, value: str) -> str:  # pylint: disable=no-self-argument
        """Ensure the path has no path parameters.

        Args:
            value: A path string

        Returns:
            The passed in value
        """
        if "{" in value:
            raise ValueError("path parameters are not supported for static files")
        return normalize_path(value)

    @validator("file_system", always=True)
    def validate_file_system(  # pylint: disable=no-self-argument
        cls, value: "FileSystemProtocol"
    ) -> "FileSystemProtocol":
        """Ensure the value is a file system spec.

        Args:
            value: A file system spec.

        Returns:
            A file system spec.
        """
        if not (callable(getattr(value, "info", None)) and callable(getattr(value, "open", None))):
            raise ValueError("file_system must adhere to the FileSystemProtocol type")
        return value

    def to_static_files_app(self) -> "ASGIRouteHandler":
        """Return an ASGI app serving static files based on the config.

        Returns:
            [StaticFiles][starlite.static_files.StaticFiles]
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
