# pylint: disable=unused-argument, import-outside-toplevel
import os
from abc import ABC, abstractmethod
from copy import copy
from http.cookies import SimpleCookie
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

from pydantic import BaseConfig, BaseModel, FilePath, validator
from pydantic.generics import GenericModel
from pydantic_openapi_schema.v3_1_0 import Header
from starlette.background import BackgroundTask as StarletteBackgroundTask
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from starlette.datastructures import State as StarletteStateClass
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.responses import FileResponse, RedirectResponse
from starlette.responses import Response as StarletteResponse
from starlette.responses import StreamingResponse
from typing_extensions import Literal, ParamSpec

from starlite.openapi.enums import OpenAPIType

P = ParamSpec("P")

if TYPE_CHECKING:
    from pydantic.fields import ModelField

    from starlite.app import Starlite
    from starlite.enums import MediaType
    from starlite.response import TemplateResponse


class BackgroundTask(StarletteBackgroundTask):
    def __init__(self, func: Callable[P, Any], *args: P.args, **kwargs: P.kwargs) -> None:
        """A container for a 'background' task function. Background tasks are
        called once a Response finishes.

        Args:
            func: A sync or async function to call as the background task.
            *args: Args to pass to the func.
            **kwargs: Kwargs to pass to the func
        """
        super().__init__(func, *args, **kwargs)


class BackgroundTasks(StarletteBackgroundTasks):
    def __init__(self, tasks: List[BackgroundTask]):
        """A container for multiple 'background' task functions. Background
        tasks are called once a Response finishes.

        Args:
            tasks: A list of [BackgroundTask][starlite.datastructures.BackgroundTask] instances.
        """
        super().__init__(tasks=tasks)


class State(StarletteStateClass):
    """An object that can be used to store arbitrary state.

    Used for `request.state` and `app.state`.

    Allows attribute access using . notation.
    """

    def __copy__(self) -> "State":
        """Returns a shallow copy of the given state object.

        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state))

    def copy(self) -> "State":
        """Returns a shallow copy of the given state object."""
        return copy(self)


class Cookie(BaseModel):
    """Container class for defining a cookie using the 'Set-Cookie' header.

    See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie for more details regarding this header.
    """

    key: str
    """Key for the cookie."""
    value: Optional[str] = None
    """Value for the cookie, if none given defaults to empty string."""
    max_age: Optional[int] = None
    """Maximal age of the cookie before its invalidated."""
    expires: Optional[int] = None
    """Expiration date as unix MS timestamp."""
    path: str = "/"
    """Path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: Optional[str] = None
    """Domain for which the cookie is valid."""
    secure: Optional[bool] = None
    """Https is required for the cookie."""
    httponly: Optional[bool] = None
    """Forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """Controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""
    description: Optional[str] = None
    """Description of the response cookie header for OpenAPI documentation"""
    documentation_only: bool = False
    """Defines the Cookie instance as for OpenAPI documentation purpose only"""

    def to_header(self, **kwargs: Any) -> str:
        """Return a string representation suitable to be sent as HTTP headers.

        Args:
            **kwargs: Passed to [SimpleCookie][http.cookies.SimpleCookie]
        """

        simple_cookie: SimpleCookie = SimpleCookie()
        simple_cookie[self.key] = self.value or ""
        if self.max_age:
            simple_cookie[self.key]["max-age"] = self.max_age
        cookie_dict = self.dict()
        for key in ["expires", "path", "domain", "secure", "httponly", "samesite"]:
            if cookie_dict[key] is not None:
                simple_cookie[self.key][key] = cookie_dict[key]
        return simple_cookie.output(**kwargs).strip()


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

    @abstractmethod
    def to_response(
        self, headers: Dict[str, Any], media_type: Union["MediaType", str], status_code: int, app: "Starlite"
    ) -> R:  # pragma: no cover
        """Abstract method that should be implemented by subclasses. Returns a
        Starlette compatible Response instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.

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
    ) -> FileResponse:
        """Creates a FileResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.

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
        self, headers: Dict[str, Any], media_type: Union["MediaType", str], status_code: int, app: "Starlite"
    ) -> RedirectResponse:
        """Creates a RedirectResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.

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
        self, headers: Dict[str, Any], media_type: Union["MediaType", str], status_code: int, app: "Starlite"
    ) -> StreamingResponse:
        """Creates a StreamingResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.

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
        self, headers: Dict[str, Any], media_type: Union["MediaType", str], status_code: int, app: "Starlite"
    ) -> "TemplateResponse":
        """Creates a TemplateResponse instance.

        Args:
            headers: A dictionary of headers.
            media_type: A string or member of the [MediaType][starlite.enums.MediaType] enum.
            status_code: A response status code.
            app: The [Starlite][starlite.app.Starlite] application instance.

        Raises:
            [ImproperlyConfiguredException][starlite.exceptions.ImproperlyConfiguredException]: if app.template_engine
                is not configured.

        Returns:
            A TemplateResponse instance
        """
        from starlite.exceptions import ImproperlyConfiguredException
        from starlite.response import TemplateResponse

        if not app.template_engine:
            raise ImproperlyConfiguredException("Template engine is not configured")
        return TemplateResponse(
            background=self.background,
            context=self.context,
            headers=headers,
            status_code=status_code,
            template_engine=app.template_engine,
            template_name=self.name,
        )


class ResponseHeader(Header):
    """Container type for a response header."""

    documentation_only: bool = False
    """defines the ResponseHeader instance as for OpenAPI documentation purpose only"""
    value: Any = None
    """value to set for the response header"""

    @validator("value", always=True)
    def validate_value(cls, value: Any, values: Dict[str, Any]) -> Any:  # pylint: disable=no-self-argument
        """Ensures that either value is set or the instance is for
        documentation_only."""
        if values.get("documentation_only") or value is not None:
            return value
        raise ValueError("value must be set if documentation_only is false")


class UploadFile(StarletteUploadFile):
    @classmethod
    def __modify_schema__(cls, field_schema: Dict[str, Any], field: Optional["ModelField"]) -> None:
        """Creates a pydantic JSON schema.

        Args:
            field_schema: The schema being generated for the field.
            field: the model class field.

        Returns:
            None
        """
        if field:
            field_schema.update({"type": OpenAPIType.STRING.value, "contentMediaType": "application/octet-stream"})
