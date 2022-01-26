from contextlib import suppress
from typing import TYPE_CHECKING, Any, Dict, Generic, TypeVar, cast

from orjson import JSONDecodeError, loads
from pydantic.fields import SHAPE_LIST, SHAPE_SINGLETON, ModelField
from starlette.datastructures import FormData, UploadFile
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket

from starlite.enums import RequestEncodingType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.parsers import parse_query_params
from starlite.types import Method

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):  # pragma: no cover
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException(
                "user is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException(
                "auth is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)

    @property
    def method(self) -> Method:
        return cast(Method, self.scope["method"])

    async def json(self) -> Any:
        if not hasattr(self, "_json"):
            body = await self.body()
            self._json = loads(body)
        return self._json


class WebSocket(StarletteWebSocket, Generic[User, Auth]):  # pragma: no cover
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException(
                "user is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException(
                "auth is not defined in scope, you should install an AuthMiddleware to set it"
            )
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)


def handle_multipart(media_type: RequestEncodingType, form_data: FormData, field: ModelField) -> Any:
    """
    Transforms the multidict into a regular dict, try to load json on all non-file values.

    Supports lists.
    """
    values_dict: Dict[str, Any] = {}
    for key, value in form_data.multi_items():
        if not isinstance(value, UploadFile):
            with suppress(JSONDecodeError):
                value = loads(value)
        if values_dict.get(key):
            if isinstance(values_dict[key], list):
                values_dict[key].append(value)
            else:
                values_dict[key] = [values_dict[key], value]
        else:
            values_dict[key] = value
    if media_type == RequestEncodingType.MULTI_PART:
        if field.shape is SHAPE_LIST:
            return list(values_dict.values())
        if field.shape is SHAPE_SINGLETON and field.type_ is UploadFile and values_dict:
            return list(values_dict.values())[0]
    return values_dict
