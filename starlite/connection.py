from typing import TYPE_CHECKING, Any, Dict, Generic, TypeVar, cast

from orjson import loads
from starlette.requests import Request as StarletteRequest
from starlette.websockets import WebSocket as StarletteWebSocket

from starlite.exceptions import ImproperlyConfiguredException
from starlite.parsers import parse_query_params
from starlite.types import Method

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite

User = TypeVar("User")
Auth = TypeVar("Auth")


class Request(StarletteRequest, Generic[User, Auth]):
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)

    @property
    def method(self) -> Method:
        return cast(Method, self.scope["method"])

    async def json(self) -> Any:
        """
        Method to retrieve the json request body from the request.

        This method overrides the Starlette method using the much faster orjson.loads() function
        """
        if not hasattr(self, "_json"):
            body = self.scope.get("_body")
            if not body:
                body = self.scope["_body"] = await self.body()
            self._json = loads(body or "null")  # pylint: disable=attribute-defined-outside-init
        return self._json


class WebSocket(StarletteWebSocket, Generic[User, Auth]):
    @property
    def app(self) -> "Starlite":
        return cast("Starlite", self.scope["app"])

    @property
    def user(self) -> User:
        if "user" not in self.scope:
            raise ImproperlyConfiguredException("'user' is not defined in scope, install an AuthMiddleware to set it")
        return cast(User, self.scope["user"])

    @property
    def auth(self) -> Auth:
        if "auth" not in self.scope:
            raise ImproperlyConfiguredException("'auth' is not defined in scope, install an AuthMiddleware to set it")
        return cast(Auth, self.scope["auth"])

    @property
    def query_params(self) -> Dict[str, Any]:  # type: ignore[override]
        return parse_query_params(self)
