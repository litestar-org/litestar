from litestar.config.app import AppConfig
from litestar.plugins import InitPlugin
from litestar.security.jwt import JWTAuth, JWTAuthenticationMiddleware


class JWTPlugin(InitPlugin):
    def __init__(self, jwt_auth: JWTAuth) -> None:
        self.jwt_auth = jwt_auth

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Handle app init by injecting middleware, guards etc. into the app. This method can be used only on the app
        level.
        """
        app_config.middleware.append(JWTAuthenticationMiddleware(self.jwt_auth))
        self.configure_openapi(app_config, self.jwt_auth)

        return app_config
