from typing import Any, Dict, Generic, Type

from pydantic_openapi_schema.v3_1_0 import (
    Components,
    SecurityRequirement,
    SecurityScheme,
)

from starlite.middleware.base import DefineMiddleware
from starlite.middleware.session.base import BaseBackendConfig, BaseSessionBackend
from starlite.security.base import AbstractSecurityConfig, UserType
from starlite.security.session_auth.middleware import (
    MiddlewareWrapper,
    SessionAuthMiddleware,
)


class SessionAuth(Generic[UserType], AbstractSecurityConfig[UserType, Dict[str, Any]]):
    """Session Based Security Backend."""

    session_backend_config: BaseBackendConfig
    """A session backend config."""

    authentication_middleware_class: Type[SessionAuthMiddleware] = SessionAuthMiddleware
    """The authentication middleware class to use.

    Must inherit from [SessionAuthMiddleware][starlite.security.session_auth.middleware.SessionAuthMiddleware]
    """

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
    def session_backend(self) -> BaseSessionBackend:
        """Create a session backend.

        Returns:
            A subclass of [BaseSessionBackend][starlite.middleware.session.base.BaseSessionBackend]
        """
        return self.session_backend_config._backend_class(config=self.session_backend_config)

    @property
    def openapi_components(self) -> Components:
        """Create OpenAPI documentation for the Session Authentication schema used.

        Returns:
            An [Components][pydantic_openapi_schema.v3_1_0.components.Components] instance.
        """
        return Components(
            securitySchemes={
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

        [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] for the auth
        backend.

        Returns:
            An OpenAPI 3.1 [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement] dictionary.
        """
        return {"sessionCookie": []}
