# pylint: disable=unused-argument, import-outside-toplevel
import os
from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Dict,
    Generator,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseConfig, FilePath, validator
from pydantic.generics import GenericModel
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse

from starlite.datastructures.background_tasks import BackgroundTask, BackgroundTasks
from starlite.datastructures.cookie import Cookie
from starlite.enums import MediaType

if TYPE_CHECKING:

    from starlite.app import Starlite
    from starlite.connection import Request
    from starlite.response import TemplateResponse


R = TypeVar("R", bound=StarletteResponse)


class ResponseContainer(GenericModel, ABC, Generic[R]):
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    background: Optional[Union[BackgroundTask, BackgroundTasks]] = None
    """
        A [BackgroundTask][starlite.datastructures.BackgroundTask] instance or
        [BackgroundTasks][starlite.datastructures.BackgroundTasks] to execute after the response is finished.
        Defaults to None.
    """
    headers: Dict[str, Any] = {}
    """A string/string dictionary of response headers. Header keys are insensitive. Defaults to None."""
    cookies: List[Cookie] = []
    """A list of Cookie instances to be set under the response 'Set-Cookie' header. Defaults to None."""
    media_type: Optional[Union[MediaType, str]] = None
    """If defined, overrides the media type configured in the route decorator"""

    @abstractmethod
    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> R:  # pragma: no cover
        """Abstract method that should be implemented by subclasses. Returns a
        Starlette compatible Response instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.
            request: A [Request][starlite.connection.request.Request] instance.

        Returns:
            A Response Object
        """
        raise NotImplementedError("not implemented")


class File(ResponseContainer[FileResponse]):
    """Container type for returning File responses."""

    path: FilePath
    """Path to the file to send"""
    filename: str
    """The filename"""
    stat_result: Optional[os.stat_result] = None
    """File statistics"""

    @validator("stat_result", always=True)
    def validate_status_code(  # pylint: disable=no-self-argument
        cls, value: Optional[os.stat_result], values: Dict[str, Any]
    ) -> os.stat_result:
        """Set the stat_result value for the given filepath."""
        return value or os.stat(cast("str", values.get("path")))

    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> FileResponse:
        """Creates a FileResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.
            request: A [Request][starlite.connection.request.Request] instance.

        Returns:
            A FileResponse instance
        """
        return FileResponse(
            background=self.background,
            filename=self.filename,
            headers=headers,
            media_type=media_type,
            path=self.path,
            stat_result=self.stat_result,
            status_code=status_code,
        )


class Redirect(ResponseContainer[RedirectResponse]):
    """Container type for returning Redirect responses."""

    path: str
    """Redirection path"""

    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> RedirectResponse:
        """Creates a RedirectResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.
            request: A [Request][starlite.connection.request.Request] instance.

        Returns:
            A RedirectResponse instance
        """
        return RedirectResponse(headers=headers, status_code=status_code, url=self.path, background=self.background)


class Stream(ResponseContainer[StreamingResponse]):
    """Container type for returning Stream responses."""

    iterator: Union[
        Iterator[Union[str, bytes]],
        Generator[Union[str, bytes], Any, Any],
        AsyncIterator[Union[str, bytes]],
        AsyncGenerator[Union[str, bytes], Any],
        Type[Iterator[Union[str, bytes]]],
        Type[AsyncIterator[Union[str, bytes]]],
        Callable[[], AsyncGenerator[Union[str, bytes], Any]],
        Callable[[], Generator[Union[str, bytes], Any, Any]],
    ]
    """Iterator, Generator or async Iterator or Generator returning stream chunks"""

    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> StreamingResponse:
        """Creates a StreamingResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.
            request: A [Request][starlite.connection.request.Request] instance.

        Returns:
            A StreamingResponse instance
        """

        return StreamingResponse(
            background=self.background,
            content=self.iterator if isinstance(self.iterator, (Iterable, AsyncIterable)) else self.iterator(),
            headers=headers,
            media_type=media_type,
            status_code=status_code,
        )


class Template(ResponseContainer["TemplateResponse"]):
    """Container type for returning Template responses."""

    name: str
    """Path-like name for the template to be rendered, e.g. "index.html"."""
    context: Optional[Dict[str, Any]] = None
    """A dictionary of key/value pairs to be passed to the temple engine's render method. Defaults to None."""

    def to_response(
        self,
        headers: Dict[str, Any],
        media_type: Union["MediaType", str],
        status_code: int,
        app: "Starlite",
        request: "Request",
    ) -> "TemplateResponse":
        """Creates a TemplateResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.
            request: A [Request][starlite.connection.request.Request] instance

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: if app.template_engine
                is not configured.

        Returns:
            A TemplateResponse instance
        """
        from starlite.exceptions import ImproperlyConfiguredException
        from starlite.response import TemplateResponse

        context = self.context or {}
        if not app.template_engine:
            raise ImproperlyConfiguredException("Template engine is not configured")
        return TemplateResponse(
            background=self.background,
            context={**context, "request": request},
            headers=headers,
            status_code=status_code,
            template_engine=app.template_engine,
            template_name=self.name,
        )
