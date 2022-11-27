from abc import ABC
from typing import (
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseConfig
from pydantic.generics import GenericModel

from starlite.datastructures import Provide
from starlite.handlers import BaseRouteHandler
from starlite.middleware.authentication import AbstractAuthenticationMiddleware
from starlite.types import BeforeMessageSendHookHandler, Guard, Scopes, SyncOrAsyncUnion

UserType = TypeVar("UserType")
AuthType = TypeVar("AuthType")

RetrieveUserHandler = Callable[[AuthType], SyncOrAsyncUnion[UserType]]


class AbstractSecurityConfig(ABC, Generic[UserType, AuthType], GenericModel):
    """A base class for Security Configs - this class can be used on the application level
    or be manually configured on the router / controller level to provide auth.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    authentication_middleware_class: Type[AbstractAuthenticationMiddleware]
    """
    The authentication middleware class to use. Must inherit from [AbstractAuthenticationMiddleware][starlite.middleware.authentication.AbstractAuthenticationMiddleware]
    """
    guards: Optional[Iterable[Guard]] = None
    """
    An iterable of guards to call for requests, providing authorization functionalities.
    """
    exclude: Optional[Union[str, List[str]]] = None
    """
    A pattern or list of patterns to skip in the authentication middleware.
    """
    exclude_opt_key: Optional[str] = None
    """
    An identifier to use on routes to disable authentication and authorization checks for a particular route.
    """
    scopes: Optional[Scopes] = None
    """
    ASGI scopes processed by the authentication middleware, if None both 'http' and 'websocket' will be processed.
    """
    route_handlers: Optional[Iterable[BaseRouteHandler]] = None
    """
    An optional iterable of route handlers to register.
    """
    dependencies: Optional[Dict[str, Provide]] = None
    """
    An optional dictionary of dependency providers.
    """
    after_send_handler: Optional[BeforeMessageSendHookHandler] = None
    """
    Optional handler to call before sending the ASGI message.

    Notes:
    - This handler allows modifying headers on the out going data , as well as perform side-effects such
        as executing DB calls etc.
    """
    retrieve_user_handler: RetrieveUserHandler
    """
    Callable that receives the 'auth' value form the authentication middleware and returns a 'user' value.

    Notes:
    - User and Auth can be any arbitrary values specified by the security backend.
    - The User and Auth values will be set by the middleware as `scope["user"]` and `scope["auth"]` respectively.
        Once provided, they can access via the `connection.user` and `connection.auth` properties.
    - The callable can be sync or async. If it is sync, it will be wrapped to support async.
    """
