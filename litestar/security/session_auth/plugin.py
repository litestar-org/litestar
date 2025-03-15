from copy import copy

from litestar.config.app import AppConfig
from litestar.middleware.session import SessionMiddleware
from litestar.plugins import InitPlugin
from litestar.security.session_auth import SessionAuth, SessionAuthMiddleware


class SessionPlugin(InitPlugin):
    """Session Plugin."""

    def __init__(self, session_auth: SessionAuth):
        self.session_auth = session_auth

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        if self.session_auth.guards:
            app_config.guards.extend(self.session_auth.guards)
        if self.session_auth.dependencies:
            app_config.dependencies.update(self.session_auth.dependencies)
        if self.session_auth.route_handlers:
            app_config.route_handlers.extend(self.session_auth.route_handlers)
        if self.session_auth.type_encoders is None:
            self.type_encoders = app_config.type_encoders

        if app_config.openapi_config:
            app_config.openapi_config = copy(app_config.openapi_config)
            if isinstance(app_config.openapi_config.components, list):
                app_config.openapi_config.components.append(self.session_auth.openapi_components)
            else:
                app_config.openapi_config.components = [
                    self.session_auth.openapi_components,
                    app_config.openapi_config.components,
                ]

            if isinstance(app_config.openapi_config.security, list):
                app_config.openapi_config.security.append(self.session_auth.security_requirement)
            else:
                app_config.openapi_config.security = [self.session_auth.security_requirement]

        app_config.middleware.append(SessionMiddleware(self.session_auth.session_backend))
        app_config.middleware.append(SessionAuthMiddleware(self.session_auth))
        return app_config
