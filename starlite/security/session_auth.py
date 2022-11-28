from typing import TYPE_CHECKING, Any, Generic, Type

from pydantic_openapi_schema.v3_1_0 import (
    Components,
    SecurityRequirement,
    SecurityScheme,
)

from starlite.exceptions import NotAuthorizedException
from starlite.middleware import ExceptionHandlerMiddleware
from starlite.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from starlite.middleware.base import DefineMiddleware
from starlite.middleware.session.base import BaseBackendConfig, SessionMiddleware
from starlite.security.base import AbstractSecurityConfig, AuthType, UserType
from starlite.types import Empty

if TYPE_CHECKING:
    from starlite.connection import ASGIConnection
    from starlite.types import ASGIApp, Receive, Scope, Send


class SessionAuth(Generic[AuthType, UserType], AbstractSecurityConfig[AuthType, UserType]):
    """Session Based Security Backend."""

    session_backend_config: Type[BaseBackendConfig]
    """A session backend config."""

    @property
    def middleware(self) -> DefineMiddleware:
        """Use this property to insert the config into a middleware list on one of the application layers.

        Examples:
            ```python
            from typing import Any
            from os import urandom

            from starlite import Starlite, Request, get
            from starlite_session import SessionAuth


            async def retrieve_user_from_session(session: dict[str, Any]) -> Any:
                # implement logic here to retrieve a 'user' datum given the session dictionary
                ...


            session_auth_config = SessionAuth(
                secret=urandom(16), retrieve_user_handler=retrieve_user_from_session
            )


            @get("/")
            def my_handler(request: Request) -> None:
                ...


            app = Starlite(route_handlers=[my_handler], middleware=[session_auth_config.middleware])
            ```

        Returns:
            An instance of DefineMiddleware including 'self' as the config kwarg value.
        """
        return DefineMiddleware(MiddlewareWrapper, config=self)

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the Session Authentication schema used.

        Returns:
            An [Components][pydantic_schema_pydantic.v3_1_0.components.Components] instance.
        """
        return Components(
            securitySchemes={
                "sessionCookie": SecurityScheme(
                    type="apiKey",
                    name="Set-Cookie",
                    security_scheme_in="cookie",
                    description="Session cookie authentication.",
                )
            }
        )

    @property
    def security_requirement(self) -> SecurityRequirement:
        """Return OpenAPI 3.1.

        [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] for the auth
        backend.

        Returns:
            An OpenAPI 3.1 [SecurityRequirement][pydantic_schema_pydantic.v3_1_0.security_requirement.SecurityRequirement] dictionary.
        """
        return {"sessionCookie": []}


class MiddlewareWrapper:
    """Wrapper class that serves as the middleware entry point."""

    def __init__(self, app: "ASGIApp", config: SessionAuth):
        """Wrap the SessionAuthMiddleware inside ExceptionHandlerMiddleware, and it wraps this inside SessionMiddleware.
        This allows the auth middleware to raise exceptions and still have the response handled, while having the
        session cleared.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            config: An instance of SessionAuth.
        """
        self.app = app
        self.config = config
        self.has_wrapped_middleware = False

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """Handle creating a middleware stack and calling it.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if not self.has_wrapped_middleware:
            starlite_app = scope["app"]
            auth_middleware = SessionAuthMiddleware(app=self.app, config=self.config)
            exception_middleware = ExceptionHandlerMiddleware(
                app=auth_middleware,
                exception_handlers=starlite_app.exception_handlers or {},
                debug=starlite_app.debug,
            )
            self.app = SessionMiddleware(
                app=exception_middleware,
                backend=self.config.session_backend_config._backend_class(config=self.config.session_backend_config),
            )
            self.has_wrapped_middleware = True
        await self.app(scope, receive, send)


class SessionAuthMiddleware(AbstractAuthenticationMiddleware):
    """Session Authentication Middleware."""

    def __init__(self, app: "ASGIApp", config: SessionAuth):
        """Session based authentication middleware.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            config: An instance of SessionAuth.
        """
        super().__init__(
            app=app, exclude=config.exclude, exclude_from_auth_key=config.exclude_opt_key, scopes=config.scopes
        )
        self.config = config

    async def authenticate_request(self, connection: "ASGIConnection[Any, Any, Any]") -> AuthenticationResult:
        """Authenticate an incoming connection.

        Args:
            connection: A Starlette 'HTTPConnection' instance.

        Raises:
            [NotAuthorizedException][starlite.exceptions.NotAuthorizedException]: if session data is empty or user
                is not found.

        Returns:
            [AuthenticationResult][starlite.middleware.authentication.AuthenticationResult]
        """
        if not connection.session or connection.session is Empty:  # type: ignore
            # the assignment of 'Empty' forces the session middleware to clear session data.
            connection.scope["session"] = Empty
            raise NotAuthorizedException("no session data found")

        user = await self.config.retrieve_user_handler(connection.session)  # type: ignore

        if not user:
            connection.scope["session"] = Empty
            raise NotAuthorizedException("no user correlating to session found")

        return AuthenticationResult(user=user, auth=connection.session)
