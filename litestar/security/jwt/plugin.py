from copy import copy

from litestar.config.app import AppConfig
from litestar.plugins import InitPlugin
from litestar.security.jwt import JWTAuthenticationMiddleware, JWTAuth


class JWTPlugin(InitPlugin):
    def __init__(self, jwt_auth: JWTAuth) -> None:
        self.jwt_auth = jwt_auth

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Handle app init by injecting middleware, guards etc. into the app. This method can be used only on the app
        level.
        """
        app_config.middleware.append(JWTAuthenticationMiddleware(self.jwt_auth))
        if app_config.openapi_config:
            app_config.openapi_config = copy(app_config.openapi_config)
            if isinstance(app_config.openapi_config.components, list):
                app_config.openapi_config.components.append(self.jwt_auth.openapi_components)
            else:
                app_config.openapi_config.components = [
                    self.jwt_auth.openapi_components,
                    app_config.openapi_config.components,
                ]

            if isinstance(app_config.openapi_config.security, list):
                app_config.openapi_config.security.append(self.jwt_auth.security_requirement)
            else:
                app_config.openapi_config.security = [self.jwt_auth.security_requirement]
        return app_config
