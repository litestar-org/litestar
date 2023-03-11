from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, Iterable

from pydantic_openapi_schema.v3_1_0 import Components, SecurityRequirement, SecurityScheme

from starlite.middleware.base import DefineMiddleware
from starlite.middleware.session.base import BaseBackendConfig, BaseSessionBackendT
from starlite.security.base import AbstractSecurityConfig, UserType
from starlite.security.session_auth.middleware import MiddlewareWrapper, SessionAuthMiddleware

__all__ = ("SessionAuth",)

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.di import Provide
    from starlite.types import ControllerRouterHandler, Guard, Scopes, SyncOrAsyncUnion, TypeEncodersMap


@dataclass
class SessionAuth(Generic[UserType, BaseSessionBackendT], AbstractSecurityConfig[UserType, Dict[str, Any]]):
    """Session Based Security Backend."""

    session_backend_config: BaseBackendConfig[BaseSessionBackendT]
    """A session backend config."""
    retrieve_user_handler: Callable[[Any, ASGIConnection], SyncOrAsyncUnion[Any | None]]
    """Callable that receives the ``auth`` value from the authentication middleware and returns a ``user`` value.

    Notes:
        - User and Auth can be any arbitrary values specified by the security backend.
        - The User and Auth values will be set by the middleware as ``scope["user"]`` and ``scope["auth"]`` respectively.
          Once provided, they can access via the ``connection.user`` and ``connection.auth`` properties.
        - The callable can be sync or async. If it is sync, it will be wrapped to support async.

    """

    authentication_middleware_class: type[SessionAuthMiddleware] = field(default=SessionAuthMiddleware)
    """The authentication middleware class to use.

    Must inherit from :class:`SessionAuthMiddleware <starlite.security.session_auth.middleware.SessionAuthMiddleware>`
    """

    guards: Iterable[Guard] | None = field(default=None)
    """An iterable of guards to call for requests, providing authorization functionalities."""
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns to skip in the authentication middleware."""
    exclude_opt_key: str = field(default="exclude_from_auth")
    """An identifier to use on routes to disable authentication and authorization checks for a particular route."""
    scopes: Scopes | None = field(default=None)
    """ASGI scopes processed by the authentication middleware, if ``None``, both ``http`` and ``websocket`` will be
    processed."""
    route_handlers: Iterable[ControllerRouterHandler] | None = field(default=None)
    """An optional iterable of route handlers to register."""
    dependencies: dict[str, Provide] | None = field(default=None)
    """An optional dictionary of dependency providers."""

    type_encoders: TypeEncodersMap | None = field(default=None)
    """A mapping of types to callables that transform them into types supported for serialization."""

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        Examples:
            .. code-block: python

                from typing import Any
                from os import urandom

                from starlite import Starlite, Request, get
                from starlite_session import SessionAuth


                async def retrieve_user_from_session(session: dict[str, Any]) -> Any:
                    # implement logic here to retrieve a ``user`` datum given the session dictionary
                    ...


                session_auth_config = SessionAuth(
                    secret=urandom(16), retrieve_user_handler=retrieve_user_from_session
                )


                @get("/")
                def my_handler(request: Request) -> None:
                    ...


                app = Starlite(route_handlers=[my_handler], middleware=[session_auth_config.middleware])


        Returns:
            An instance of DefineMiddleware including ``self`` as the config kwarg value.
        """
        return DefineMiddleware(MiddlewareWrapper, config=self)

    @property
    def session_backend(self) -> BaseSessionBackendT:
        """Create a session backend.

        Returns:
            A subclass of :class:`BaseSessionBackend <starlite.middleware.session.base.BaseSessionBackend>`
        """
        return self.session_backend_config._backend_class(config=self.session_backend_config)

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the Session Authentication schema used.

        Returns:
            An :class:`Components <pydantic_openapi_schema.v3_1_0.components.Components>` instance.
        """
        return Components(
            securitySchemes={
                "sessionCookie": SecurityScheme(
                    type="apiKey",
                    name=self.session_backend_config.key,
                    security_scheme_in="cookie",  # pyright: ignore
                    description="Session cookie authentication.",
                )
            }
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Return OpenAPI 3.1.

        :data:`SecurityRequirement <pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement>` for the auth
        backend.

        Returns:
            An OpenAPI 3.1 :data:`SecurityRequirement <pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement>` dictionary.
        """
        return {"sessionCookie": []}
