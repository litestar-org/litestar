import os
from copy import copy
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union, cast

from pydantic import BaseConfig, BaseModel, FilePath, validator
from pydantic_openapi_schema.v3_1_0 import Header
from starlette.background import BackgroundTask
from starlette.datastructures import State as StarletteStateClass
from typing_extensions import Literal


class State(StarletteStateClass):
    """
    An object that can be used to store arbitrary state.

    Used for `request.state` and `app.state`.

    Allows attribute access using . notation.
    """

    def __copy__(self) -> "State":
        """
        Returns a shallow copy of the given state object.
        Customizes how the builtin "copy" function will work.
        """
        return self.__class__(copy(self._state))

    def copy(self) -> "State":
        """Returns a shallow copy of the given state object"""
        return copy(self)


class Cookie(BaseModel):
    """
    Container class for defining a cookie using the 'Set-Cookie' header.

    See: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie for more details regarding this header.
    """

    key: str
    """key for the cookie."""
    value: Optional[str] = None
    """value for the cookie, if none given defaults to empty string."""
    max_age: Optional[int] = None
    """maximal age before the cookie is invalidated."""
    expires: Optional[int] = None
    """expiration date as unix MS timestamp."""
    path: str = "/"
    """path fragment that must exist in the request url for the cookie to be valid. Defaults to '/'."""
    domain: Optional[str] = None
    """domain for which the cookie is valid."""
    secure: Optional[bool] = None
    """https is required for the cookie."""
    httponly: Optional[bool] = None
    """forbids javascript to access the cookie via 'Document.cookie'."""
    samesite: Literal["lax", "strict", "none"] = "lax"
    """controls whether or not a cookie is sent with cross-site requests. Defaults to 'lax'."""
    description: Optional[str] = None
    """description of the response cookie header for OpenAPI documentation"""
    documentation_only: bool = False
    """defines the Cookie instance as for OpenAPI documentation purpose only"""


class File(BaseModel):
    """
    Container type for returning File responses
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    background: Optional[BackgroundTask] = None
    """A background task to execute in parallel to the response. Defaults to None."""
    headers: Dict[str, str] = {}
    """A string/string dictionary of response headers. Header keys are insensitive. Defaults to None."""
    cookies: List[Cookie] = []
    """A list of Cookie instances to be set under the response 'Set-Cookie' header. Defaults to None."""
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
        """Set the stat_result value for the given filepath"""
        return value or os.stat(cast("str", values.get("path")))


class Redirect(BaseModel):
    """
    Container type for returning Redirect responses
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    background: Optional[BackgroundTask] = None
    """A background task to execute in parallel to the response. Defaults to None."""
    headers: Dict[str, str] = {}
    """A string/string dictionary of response headers. Header keys are insensitive. Defaults to None."""
    cookies: List[Cookie] = []
    """A list of Cookie instances to be set under the response 'Set-Cookie' header. Defaults to None."""
    path: str
    """Redirection path"""


class Stream(BaseModel):
    """
    Container type for returning Stream responses
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    background: Optional[BackgroundTask] = None
    """A background task to execute in parallel to the response. Defaults to None."""
    headers: Dict[str, str] = {}
    """A string/string dictionary of response headers. Header keys are insensitive. Defaults to None."""
    cookies: List[Cookie] = []
    """A list of Cookie instances to be set under the response 'Set-Cookie' header. Defaults to None."""
    iterator: Union[Iterator[Any], AsyncIterator[Any]]
    """Iterator returning stream chunks"""


class Template(BaseModel):
    """
    Container type for returning Template responses
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    background: Optional[BackgroundTask] = None
    """A background task to execute in parallel to the response. Defaults to None."""
    headers: Dict[str, str] = {}
    """A string/string dictionary of response headers. Header keys are insensitive. Defaults to None."""
    cookies: List[Cookie] = []
    """A list of Cookie instances to be set under the response 'Set-Cookie' header. Defaults to None."""
    name: str
    """Path-like name for the template to be rendered, e.g. "index.html"."""
    context: Optional[Dict[str, Any]] = None
    """A dictionary of key/value pairs to be passed to the temple engine's render method. Defaults to None."""


class ResponseHeader(Header):
    """
    Container type for a response header
    """

    documentation_only: bool = False
    """defines the ResponseHeader instance as for OpenAPI documentation purpose only"""
    value: Any = None
    """value to set for the response header"""

    @validator("value", always=True)
    def validate_value(cls, value: Any, values: Dict[str, Any]) -> Any:  # pylint: disable=no-self-argument
        """
        Ensures that either value is set or the instance is for documentation_only

        """
        if values.get("documentation_only") or value is not None:
            return value
        raise ValueError("value must be set if documentation_only is false")
