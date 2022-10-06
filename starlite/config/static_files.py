from typing import TYPE_CHECKING, List, cast

from pydantic import BaseModel, DirectoryPath, constr, validator
from starlette.staticfiles import StaticFiles

from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlite.types import ASGIApp


class StaticFilesConfig(BaseModel):
    """Configuration for static file service.

    To enable static files, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'static_files_config' key.
    """

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

    def to_static_files_app(self) -> "ASGIApp":
        """Returns an ASGI app serving static files based on the config.

                Returns:
        ^           [StaticFiles][starlette.static_files.StaticFiles]
        """
        static_files = StaticFiles(
            html=self.html_mode,
            check_dir=False,
            directory=str(self.directories[0]),
        )
        static_files.all_directories = self.directories  # type: ignore[assignment]
        return cast("ASGIApp", static_files)
