from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, cast

from litestar.middleware.session.base import BaseBackendConfig, BaseSessionBackendT
from litestar.openapi.spec import Components, SecurityRequirement, SecurityScheme
from litestar.security.base import AbstractSecurityConfig, UserType
from litestar.security.session_auth.middleware import SessionAuthMiddleware

__all__ = ("SessionAuth",)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from litestar.config.app import AppConfig
    from litestar.connection import ASGIConnection
    from litestar.di import Provide
    from litestar.types import ControllerRouterHandler, Guard, Method, Scopes, SyncOrAsyncUnion, TypeEncodersMap


@dataclass
class SessionAuth(Generic[UserType, BaseSessionBackendT], AbstractSecurityConfig[UserType, dict[str, Any]]):
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

    authentication_middleware_class: type[SessionAuthMiddleware] = field(default=SessionAuthMiddleware)  # pyright: ignore[reportIncompatibleVariableOverride]
    """The authentication middleware class to use.

    Must inherit from :class:`SessionAuthMiddleware <litestar.security.session_auth.middleware.SessionAuthMiddleware>`
    """

    guards: Iterable[Guard] | None = field(default=None)
    """An iterable of guards to call for requests, providing authorization functionalities."""
    exclude: str | list[str] | None = field(default=None)
    """A pattern or list of patterns to skip in the authentication middleware."""
    exclude_opt_key: str = field(default="exclude_from_auth")
    """An identifier to use on routes to disable authentication and authorization checks for a particular route."""
    exclude_http_methods: Sequence[Method] | None = field(
        default_factory=lambda: cast("Sequence[Method]", ["OPTIONS", "HEAD"])
    )
    """A sequence of http methods that do not require authentication. Defaults to ['OPTIONS', 'HEAD']"""
    scopes: Scopes | None = field(default=None)
    """ASGI scopes processed by the authentication middleware, if ``None``, both ``http`` and ``websocket`` will be
    processed."""
    route_handlers: Iterable[ControllerRouterHandler] | None = field(default=None)
    """An optional iterable of route handlers to register."""
    dependencies: dict[str, Provide] | None = field(default=None)
    """An optional dictionary of dependency providers."""

    type_encoders: TypeEncodersMap | None = field(default=None)
    """A mapping of types to callables that transform them into types supported for serialization."""

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Handle app init by injecting the session middleware, the authentication middleware, guards etc. into the app.

        Args:
            app_config: An instance of :class:`AppConfig <.config.app.AppConfig>`

        Returns:
            The :class:`AppConfig <.config.app.AppConfig>`.
        """
        app_config = super().on_app_init(app_config)
        app_config.middleware.insert(0, self.session_backend_config.middleware)
        return app_config

    @property
    def middleware(self) -> SessionAuthMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        The session middleware itself is not included: it has to be installed on the application, before this
        middleware, which :meth:`on_app_init` does.

        Examples:
            .. code-block:: python

                from typing import Any

                from litestar import Litestar, Request, get
                from litestar.connection import ASGIConnection
                from litestar.middleware.session.server_side import ServerSideSessionConfig
                from litestar.security.session_auth import SessionAuth


                async def retrieve_user_from_session(
                    session: dict[str, Any], connection: ASGIConnection
                ) -> Any:
                    # implement logic here to retrieve a ``user`` datum given the session dictionary
                    ...


                session_config = ServerSideSessionConfig()
                session_auth = SessionAuth(
                    session_backend_config=session_config,
                    retrieve_user_handler=retrieve_user_from_session,
                )


                @get("/")
                def my_handler(request: Request) -> None: ...


                app = Litestar(
                    route_handlers=[my_handler],
                    middleware=[session_config.middleware, session_auth.middleware],
                )


        Returns:
            An instance of the config's ``authentication_middleware_class``.
        """
        return self.authentication_middleware_class(
            exclude=self.exclude,
            exclude_http_methods=self.exclude_http_methods,
            exclude_opt_key=self.exclude_opt_key,
            retrieve_user_handler=self.retrieve_user_handler,
            scopes=self.scopes,
        )

    @property
    def session_backend(self) -> BaseSessionBackendT:
        """Create a session backend.

        Returns:
            A subclass of :class:`BaseSessionBackend <litestar.middleware.session.base.BaseSessionBackend>`
        """
        return self.session_backend_config._backend_class(config=self.session_backend_config)

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the Session Authentication schema used.

        Returns:
            An :class:`Components <litestar.openapi.spec.components.Components>` instance.
        """
        return Components(
            security_schemes={
                "sessionCookie": SecurityScheme(
                    type="apiKey",
                    name=self.session_backend_config.key,
                    security_scheme_in="cookie",
                    description="Session cookie authentication.",
                )
            }
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Return OpenAPI 3.1.

        :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>` for the auth
        backend.

        Returns:
            An OpenAPI 3.1 :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>` dictionary.
        """
        return {"sessionCookie": []}
