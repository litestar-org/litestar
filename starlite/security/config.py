from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
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

from pydantic import BaseConfig, validator
from pydantic.generics import GenericModel

from starlite.connection import ASGIConnection
from starlite.datastructures import Provide
from starlite.handlers import BaseRouteHandler
from starlite.middleware.authentication import AbstractAuthenticationMiddleware
from starlite.types import BeforeMessageSendHookHandler, Guard, Scopes, SyncOrAsyncUnion
from starlite.utils.sync import AsyncCallable

UserType = TypeVar("UserType")
AuthType = TypeVar("AuthType")

if TYPE_CHECKING:
    from pydantic_openapi_schema.v3_1_0 import Components, SecurityRequirement

    from starlite.middleware.base import DefineMiddleware


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
    retrieve_user_handler: Callable[[AuthType, ASGIConnection], SyncOrAsyncUnion[UserType]]
    """
    Callable that receives the 'auth' value form the authentication middleware and returns a 'user' value.

    Notes:
    - User and Auth can be any arbitrary values specified by the security backend.
    - The User and Auth values will be set by the middleware as `scope["user"]` and `scope["auth"]` respectively.
        Once provided, they can access via the `connection.user` and `connection.auth` properties.
    - The callable can be sync or async. If it is sync, it will be wrapped to support async.
    """

    @validator("retrieve_user_handler")
    def validate_retrieve_user_handler(  # pylint: disable=no-self-argument
        cls, value: Callable[[AuthType], SyncOrAsyncUnion[UserType]]
    ) -> Any:
        """Ensure that the passed in value does not get bound.

        Args:
            value: A callable fulfilling the RetrieveUserHandler type.

        Returns:
            An instance of AsyncCallable wrapping the callable.
        """
        return AsyncCallable(value)

    @property
    @abstractmethod
    def openapi_components(self) -> "Components":  # pragma: no cover
        """Create OpenAPI documentation for the JWT auth schema used.

        Returns:
            An [Components][pydantic_schema_pydantic.v3_1_0.components.Components] instance.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def security_requirement(self) -> "SecurityRequirement":  # pragma: no cover
        """Return OpenAPI 3.1.

        [SecurityRequirement][pydantic_schema_pydantic.v3_1_0.security_requirement.SecurityRequirement] for the auth
        backend.

        Returns:
            An OpenAPI 3.1 [SecurityRequirement][pydantic_schema_pydantic.v3_1_0.security_requirement.SecurityRequirement] dictionary.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def middleware(self) -> "DefineMiddleware":  # pragma: no cover
        """Create an instance of the config's 'authentication_middleware_class' attribute and any required kwargs,
        wrapping it in Starlite's `DefineMiddleware`.

        Returns:
            An instance of [DefineMiddleware][starlite.middleware.base.DefineMiddleware].
        """
        raise NotImplementedError
