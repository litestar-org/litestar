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

        self.configure_openapi(app_config, self.session_auth)

        app_config.middleware.append(SessionMiddleware(self.session_auth.session_backend))
        app_config.middleware.append(SessionAuthMiddleware(self.session_auth))
        return app_config
