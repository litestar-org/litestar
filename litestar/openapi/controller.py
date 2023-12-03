from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any, Callable, Literal

from litestar.controller import Controller
from litestar.enums import MediaType, OpenAPIMediaType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.exceptions.openapi_exceptions import OpenAPINotFoundException
from litestar.handlers import HTTPRouteHandler, get
from litestar.response.base import ASGIResponse
from litestar.serialization import encode_json
from litestar.types.helper_types import NoValidate

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.spec.open_api import OpenAPI

__all__ = ("OpenAPIController",)


def openapi_guard(request: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    if not request.app.openapi_config:  # pragma: no cover
        raise ImproperlyConfiguredException("Litestar has not been instantiated with an OpenAPIConfig")

    if not isinstance(route_handler, HTTPRouteHandler):
        raise RuntimeError("Guard should be used with HTTPRouteHandler instances only")

    owner = route_handler.owner
    if not owner or not isinstance(owner, OpenAPIController):
        raise RuntimeError("OpenAPIController should be the owner of this route handler")

    asgi_root_path = set(filter(None, request.scope.get("root_path", "").split("/")))
    full_request_path = set(filter(None, request.url.path.split("/")))
    request_path = full_request_path.difference(asgi_root_path)
    root_path = set(filter(None, owner.path.split("/")))

    config = request.app.openapi_config

    if (request_path == root_path and config.root_schema_site in config.enabled_endpoints) or (
        request_path & config.enabled_endpoints
    ):
        return

    media_type = (
        MediaType.JSON
        if route_handler.media_type in (OpenAPIMediaType.OPENAPI_JSON, OpenAPIMediaType.OPENAPI_YAML)
        else MediaType(route_handler.media_type)
    )
    raise OpenAPINotFoundException(
        body=owner.render_404_page() if media_type == MediaType.HTML else b"null", media_type=media_type
    )


class OpenAPIController(Controller):
    """Controller for OpenAPI endpoints."""

    guards = [openapi_guard]

    path: str = "/schema"
    """Base path for the OpenAPI documentation endpoints."""
    style: str = "body { margin: 0; padding: 0 }"
    """Base styling of the html body."""
    redoc_version: str = "next"
    """Redoc version to download from the CDN."""
    swagger_ui_version: str = "5.1.3"
    """SwaggerUI version to download from the CDN."""
    stoplight_elements_version: str = "7.7.18"
    """StopLight Elements version to download from the CDN."""
    rapidoc_version: str = "9.3.4"
    """RapiDoc version to download from the CDN."""
    favicon_url: str = ""
    """URL to download a favicon from."""
    redoc_google_fonts: bool = True
    """Download google fonts via CDN.

    Should be set to ``False`` when not using a CDN.
    """
    redoc_js_url: str = f"https://cdn.jsdelivr.net/npm/redoc@{redoc_version}/bundles/redoc.standalone.js"
    """Download url for the Redoc JS bundle."""
    swagger_css_url: str = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{swagger_ui_version}/swagger-ui.css"
    """Download url for the Swagger UI CSS bundle."""
    swagger_ui_bundle_js_url: str = (
        f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{swagger_ui_version}/swagger-ui-bundle.js"
    )
    """Download url for the Swagger UI JS bundle."""
    swagger_ui_standalone_preset_js_url: str = (
        f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{swagger_ui_version}/swagger-ui-standalone-preset.js"
    )
    """Download url for the Swagger Standalone Preset JS bundle."""
    swagger_ui_init_oauth: dict[Any, Any] | bytes = {}
    """
    JSON to initialize Swagger UI OAuth2 by calling the `initOAuth` method.

    Refer to the following URL for details:
    `Swagger-UI <https://swagger.io/docs/open-source-tools/swagger-ui/usage/oauth2/>`_.
    """
    stoplight_elements_css_url: str = (
        f"https://unpkg.com/@stoplight/elements@{stoplight_elements_version}/styles.min.css"
    )
    """Download url for the Stoplight Elements CSS bundle."""
    stoplight_elements_js_url: str = (
        f"https://unpkg.com/@stoplight/elements@{stoplight_elements_version}/web-components.min.js"
    )
    """Download url for the Stoplight Elements JS bundle."""
    rapidoc_js_url: str = f"https://unpkg.com/rapidoc@{rapidoc_version}/dist/rapidoc-min.js"
    """Download url for the RapiDoc JS bundle."""

    # internal
    _dumped_json_schema: str = ""
    _dumped_yaml_schema: bytes = b""
    # until swagger-ui supports v3.1.* of OpenAPI officially, we need to modify the schema for it and keep it
    # separate from the redoc version of the schema, which is unmodified.
    dto = None
    return_dto = None

    @property
    def favicon(self) -> str:
        """Return favicon ``<link>`` tag, if applicable.

        Returns:
            A ``<link>`` tag if ``self.favicon_url`` is not empty, otherwise returns a placeholder meta tag.
        """
        return f"<link rel='icon' type='image/x-icon' href='{self.favicon_url}'>" if self.favicon_url else "<meta/>"

    @cached_property
    def render_methods_map(
        self,
    ) -> dict[Literal["redoc", "swagger", "elements", "rapidoc"], Callable[[OpenAPI, bytes], bytes]]:
        """Map render method names to render methods.

        Returns:
            A mapping of string keys to render methods.
        """
        return {
            "redoc": self.render_redoc,
            "swagger": self.render_swagger_ui,
            "elements": self.render_stoplight_elements,
            "rapidoc": self.render_rapidoc,
        }

    @get(
        path=["/openapi.yaml", "openapi.yml"],
        media_type=OpenAPIMediaType.OPENAPI_YAML,
        include_in_schema=False,
        sync_to_thread=False,
    )
    def retrieve_schema_yaml(self, openapi_yaml: bytes) -> ASGIResponse:
        """Return the OpenAPI schema as YAML with an ``application/vnd.oai.openapi`` Content-Type header.

        Args:
            openapi_yaml: The OpenAPI schema as YAML.

        Returns:
            A Response instance with the YAML object rendered into a string.
        """
        return ASGIResponse(body=openapi_yaml, media_type=OpenAPIMediaType.OPENAPI_YAML)

    @get(path="/openapi.json", media_type=OpenAPIMediaType.OPENAPI_JSON, include_in_schema=False, sync_to_thread=False)
    def retrieve_schema_json(self, openapi_json: bytes) -> ASGIResponse:
        """Return the OpenAPI schema as JSON with an ``application/vnd.oai.openapi+json`` Content-Type header.

        Args:
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A Response instance with the JSON object rendered into a string.
        """
        return ASGIResponse(body=openapi_json, media_type=OpenAPIMediaType.OPENAPI_JSON)

    @get(path="/", include_in_schema=False, sync_to_thread=False, media_type=MediaType.HTML)
    def root(
        self, openapi_config: NoValidate[OpenAPIConfig], openapi_schema: NoValidate[OpenAPI], openapi_json: bytes
    ) -> ASGIResponse:
        """Render a static documentation site.

         The site to be rendered is based on the ``root_schema_site`` value set in the application's
         :class:`OpenAPIConfig <.openapi.OpenAPIConfig>`. Defaults to ``redoc``.

        Args:
            openapi_config: The application's OpenAPIConfig instance.
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A response with the rendered site defined in root_schema_site.

        Raises:
            ImproperlyConfiguredException: If the application ``openapi_config`` attribute is ``None``.
        """
        render_method = self.render_methods_map[openapi_config.root_schema_site]
        return ASGIResponse(body=render_method(openapi_schema, openapi_json), media_type=MediaType.HTML)

    @get(path="/swagger", include_in_schema=False, sync_to_thread=False, media_type=MediaType.HTML)
    def swagger_ui(self, openapi_schema: NoValidate[OpenAPI], openapi_json: bytes) -> ASGIResponse:
        """Route handler responsible for rendering Swagger-UI.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A response with a rendered swagger documentation site
        """
        return ASGIResponse(body=self.render_swagger_ui(openapi_schema, openapi_json), media_type=MediaType.HTML)

    @get(path="/elements", media_type=MediaType.HTML, include_in_schema=False, sync_to_thread=False)
    def stoplight_elements(self, openapi_schema: NoValidate[OpenAPI], openapi_json: bytes) -> ASGIResponse:
        """Route handler responsible for rendering StopLight Elements.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A response with a rendered stoplight elements documentation site
        """
        return ASGIResponse(
            body=self.render_stoplight_elements(openapi_schema, openapi_json), media_type=MediaType.HTML
        )

    @get(path="/redoc", media_type=MediaType.HTML, include_in_schema=False, sync_to_thread=False)
    def redoc(self, openapi_schema: NoValidate[OpenAPI], openapi_json: bytes) -> ASGIResponse:  # pragma: no cover
        """Route handler responsible for rendering Redoc.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A response with a rendered redoc documentation site
        """
        return ASGIResponse(body=self.render_redoc(openapi_schema, openapi_json), media_type=MediaType.HTML)

    @get(path="/rapidoc", media_type=MediaType.HTML, include_in_schema=False, sync_to_thread=False)
    def rapidoc(self, openapi_schema: NoValidate[OpenAPI], openapi_json: bytes) -> ASGIResponse:
        return ASGIResponse(body=self.render_rapidoc(openapi_schema, openapi_json), media_type=MediaType.HTML)

    @get(path="/oauth2-redirect.html", media_type=MediaType.HTML, include_in_schema=False, sync_to_thread=False)
    def swagger_ui_oauth2_redirect(self) -> ASGIResponse:  # pragma: no cover
        """Route handler responsible for rendering oauth2-redirect.html page for Swagger-UI.

        Returns:
            A response with a rendered oauth2-redirect.html page for Swagger-UI.
        """
        return ASGIResponse(body=self.render_swagger_ui_oauth2_redirect(), media_type=MediaType.HTML)

    @staticmethod
    def render_swagger_ui_oauth2_redirect() -> bytes:
        """Render an HTML oauth2-redirect.html page for Swagger-UI.

        Notes:
            - override this method to customize the template.

        Returns:
            A rendered html string.
        """
        return rb"""<!doctype html>
        <html lang="en-US">
        <head>
            <title>Swagger UI: OAuth2 Redirect</title>
        </head>
        <body>
        <script>
            'use strict';
            function run () {
                var oauth2 = window.opener.swaggerUIRedirectOauth2;
                var sentState = oauth2.state;
                var redirectUrl = oauth2.redirectUrl;
                var isValid, qp, arr;

                if (/code|token|error/.test(window.location.hash)) {
                    qp = window.location.hash.substring(1).replace('?', '&');
                } else {
                    qp = location.search.substring(1);
                }

                arr = qp.split("&");
                arr.forEach(function (v,i,_arr) { _arr[i] = '"' + v.replace('=', '":"') + '"';});
                qp = qp ? JSON.parse('{' + arr.join() + '}',
                        function (key, value) {
                            return key === "" ? value : decodeURIComponent(value);
                        }
                ) : {};

                isValid = qp.state === sentState;

                if ((
                oauth2.auth.schema.get("flow") === "accessCode" ||
                oauth2.auth.schema.get("flow") === "authorizationCode" ||
                oauth2.auth.schema.get("flow") === "authorization_code"
                ) && !oauth2.auth.code) {
                    if (!isValid) {
                        oauth2.errCb({
                            authId: oauth2.auth.name,
                            source: "auth",
                            level: "warning",
                            message: "Authorization may be unsafe, passed state was changed in server. The passed state wasn't returned from auth server."
                        });
                    }

                    if (qp.code) {
                        delete oauth2.state;
                        oauth2.auth.code = qp.code;
                        oauth2.callback({auth: oauth2.auth, redirectUrl: redirectUrl});
                    } else {
                        let oauthErrorMsg;
                        if (qp.error) {
                            oauthErrorMsg = "["+qp.error+"]: " +
                                (qp.error_description ? qp.error_description+ ". " : "no accessCode received from the server. ") +
                                (qp.error_uri ? "More info: "+qp.error_uri : "");
                        }

                        oauth2.errCb({
                            authId: oauth2.auth.name,
                            source: "auth",
                            level: "error",
                            message: oauthErrorMsg || "[Authorization failed]: no accessCode received from the server."
                        });
                    }
                } else {
                    oauth2.callback({auth: oauth2.auth, token: qp, isValid: isValid, redirectUrl: redirectUrl});
                }
                window.close();
            }

            if (document.readyState !== 'loading') {
                run();
            } else {
                document.addEventListener('DOMContentLoaded', function () {
                    run();
                });
            }
        </script>
        </body>
        </html>"""

    def render_swagger_ui(self, openapi_schema: OpenAPI, openapi_json: bytes) -> bytes:
        """Render an HTML page for Swagger-UI.

        Notes:
            - override this method to customize the template.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A rendered html string.
        """
        head = f"""
          <head>
            <title>{openapi_schema.info.title}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="{self.swagger_css_url}" rel="stylesheet">
            <script src="{self.swagger_ui_bundle_js_url}" crossorigin></script>
            <script src="{self.swagger_ui_standalone_preset_js_url}" crossorigin></script>
            <style>{self.style}</style>
          </head>
        """

        body = f"""
          <body>
            <div id='swagger-container'/>
            <script type="text/javascript">
            const ui = SwaggerUIBundle({{
                spec: {openapi_json.decode('utf-8')},
                dom_id: '#swagger-container',
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
            }})
            ui.initOAuth({encode_json(self.swagger_ui_init_oauth).decode('utf-8')})
            </script>
          </body>
        """

        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """.encode()

    def render_stoplight_elements(self, openapi_schema: OpenAPI, _: bytes) -> bytes:
        """Render an HTML page for StopLight Elements.

        Notes:
            - override this method to customize the template.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.

        Returns:
            A rendered html string.
        """
        head = f"""
          <head>
            <title>{openapi_schema.info.title}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
            <link rel="stylesheet" href="{self.stoplight_elements_css_url}">
            <script src="{self.stoplight_elements_js_url}" crossorigin></script>
            <style>{self.style}</style>
          </head>
        """

        body = """
          <body>
            <elements-api
                apiDescriptionUrl="openapi.json"
                router="hash"
                layout="sidebar"
            />
          </body>
        """

        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """.encode()

    def render_rapidoc(self, openapi_schema: OpenAPI, _: bytes) -> bytes:  # pragma: no cover
        head = f"""
          <head>
            <title>{openapi_schema.info.title}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="{self.rapidoc_js_url}" crossorigin></script>
            <style>{self.style}</style>
          </head>
        """

        body = """
          <body>
            <rapi-doc spec-url="openapi.json" />
          </body>
        """

        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """.encode()

    def render_redoc(self, openapi_schema: OpenAPI, openapi_json: bytes) -> bytes:  # pragma: no cover
        """Render an HTML page for Redoc.

        Notes:
            - override this method to customize the template.

        Args:
            openapi_schema: The OpenAPI schema as an OpenAPI instance.
            openapi_json: The OpenAPI schema as JSON.

        Returns:
            A rendered html string.
        """
        head = f"""
          <head>
            <title>{openapi_schema.info.title}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            """

        if self.redoc_google_fonts:
            head += """
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            """

        head += f"""
            <script src="{self.redoc_js_url}" crossorigin></script>
            <style>
                {self.style}
            </style>
          </head>
        """

        body = f"""
          <body>
            <div id='redoc-container'/>
            <script type="text/javascript">
                Redoc.init(
                    {openapi_json.decode('utf-8')},
                    undefined,
                    document.getElementById('redoc-container')
                )
            </script>
          </body>
        """

        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """.encode()

    def render_404_page(self) -> bytes:
        """Render an HTML 404 page.

        Returns:
            A rendered html string.
        """

        return f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>404 Not found</title>
                {self.favicon}
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    {self.style}
                </style>
            </head>
            <body>
                <h1>Error 404</h1>
            </body>
        </html>
        """.encode()
