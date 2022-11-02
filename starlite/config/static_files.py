from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fsspec.implementations.local import LocalFileSystem
from pydantic import BaseConfig, BaseModel, DirectoryPath, constr, validator

from starlite.handlers import asgi
from starlite.static_files.base import StaticFiles
from starlite.types import ExceptionHandlersMap, Guard
from starlite.types.file_types import FileSystemType
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.handlers import ASGIRouteHandler


class StaticFilesConfig(BaseModel):
    """Configuration for static file service.

    To enable static files, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'static_files_config' key.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    path: constr(min_length=1)  # type: ignore
    """
        Path to serve static files from.
        Note that the path cannot contain path parameters.
    """
    directories: List[DirectoryPath]
    """
        A list of directories to serve files from.
    """
    html_mode: bool = False
    """
        Flag dictating whether or not serving html. If true, the default file will be 'index.html'.
    """
    name: Optional[str] = None
    """
        An optional string identifying the static files handler.
    """
    file_system: FileSystemType = LocalFileSystem()
    """
        The backend to use for serving files.

        Notes:
            - A backend is a class that implements the
                [StaticFilesBackend][starlite.static_files.base.StaticFilesBackend] protocol.
    """
    opt: Optional[Dict[str, Any]] = None
    """
        A string key dictionary of arbitrary values that will be added to the static files handler.
    """
    guards: Optional[List[Guard]] = None
    """
        A list of [Guard][starlite.types.Guard] callables.
    """
    exception_handlers: Optional[ExceptionHandlersMap] = None
    """
        A dictionary that maps handler functions to status codes and/or exception types.
    """

    @validator("path", always=True)
    def validate_path(cls, value: str) -> str:  # pylint: disable=no-self-argument
        """Ensures the path has no path parameters.

        Args:
            value: A path string

        Returns:
            The passed in value
        """
        if "{" in value:
            raise ValueError("path parameters are not supported for static files")
        return normalize_path(value)

    def to_static_files_app(self) -> "ASGIRouteHandler":
        """Returns an ASGI app serving static files based on the config.

                Returns:
        ^           [StaticFiles][starlette.static_files.StaticFiles]
        """
        static_files = StaticFiles(html_mode=self.html_mode, directories=self.directories, file_system=self.file_system)  # type: ignore
        return asgi(
            path=self.path,
            name=self.name,
            is_static=True,
            opt=self.opt,
            guards=self.guards,
            exception_handlers=self.exception_handlers,
        )(static_files)
