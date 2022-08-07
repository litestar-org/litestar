import os
from copy import copy
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union, cast

from pydantic import BaseConfig, BaseModel, FilePath, validator
from starlette.background import BackgroundTask
from starlette.datastructures import State as StarletteStateClass
from typing_extensions import Literal


class State(StarletteStateClass):
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
    """case insensitive key for the cookie."""
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


class StarliteType(BaseModel):
    background: Optional[BackgroundTask] = None
    headers: Dict[str, str] = {}
    cookies: List[Cookie] = []

    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False


class File(StarliteType):
    path: FilePath
    filename: str
    stat_result: Optional[os.stat_result] = None

    @validator("stat_result", always=True)
    def validate_status_code(  # pylint: disable=no-self-argument
        cls, value: Optional[os.stat_result], values: Dict[str, Any]
    ) -> os.stat_result:
        """Set the stat_result value for the given filepath"""
        return value or os.stat(cast("str", values.get("path")))


class Redirect(StarliteType):
    path: str


class Stream(StarliteType):
    iterator: Union[Iterator[Any], AsyncIterator[Any]]


class Template(StarliteType):
    name: str
    context: Optional[Dict[str, Any]]
