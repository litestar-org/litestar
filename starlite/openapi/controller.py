from typing import TYPE_CHECKING

from orjson import OPT_INDENT_2, dumps

from starlite.connection import Request
from starlite.controller import Controller
from starlite.enums import MediaType, OpenAPIMediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import get

if TYPE_CHECKING:
    from openapi_schema_pydantic.v3.v3_1_0.open_api import OpenAPI


class OpenAPIController(Controller):
    path = "/schema"
    styles = """
        body { margin: 0; padding: 0 }
    """
    redoc_version = "next"
    dumped_schema = ""

    @staticmethod
    def schema_from_request(request: Request) -> "OpenAPI":
        """Returns the openapi schema"""
        if not request.app.openapi_schema:  # pragma: no cover
            raise ImproperlyConfiguredException("Starlite has not been instantiated with OpenAPIConfig")
        return request.app.openapi_schema

    @get(path="/openapi.yaml", media_type=OpenAPIMediaType.OPENAPI_YAML, include_in_schema=False)
    def retrieve_schema_yaml(self, request: Request) -> "OpenAPI":
        """Returns the openapi schema"""
        return self.schema_from_request(request)

    @get(path="/openapi.json", media_type=OpenAPIMediaType.OPENAPI_JSON, include_in_schema=False)
    def retrieve_schema_json(self, request: Request) -> "OpenAPI":
        """Returns the openapi schema"""
        return self.schema_from_request(request)

    @get(path="/swagger", media_type=MediaType.HTML, include_in_schema=False)
    def swagger_ui(self, request: Request) -> str:
        """Endpoint that serves SwaggerUI"""
        schema = self.schema_from_request(request)
        if self.dumped_schema == "":
            # Note: Fix for Swagger rejection OpenAPI >=3.1
            # We force the version to be lower to get the default JS bundle to accept it
            # This works flawlessly as the main blocker for Swagger support for OpenAPI 3.1 is JSON schema support
            # Since we use the YAML format this is not an issue for us and we can do this trick to get support right now
            # We use deepcopy to avoid changing the actual schema on the request. Since this is a cached call the effect is minimal
            schema_copy = schema.copy()
            schema_copy.openapi = "3.0.3"
            self.dumped_schema = dumps(schema_copy.json(by_alias=True, exclude_none=True), option=OPT_INDENT_2).decode(
                "utf-8"
            )
        head = f"""
          <head>
            <title>{schema.info.title}</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
            <style>
                {self.styles}
            </style>
          </head>
        """
        body = f"""
          <body>
            <div id='swagger-container'></div>
            <script>
            const ui = SwaggerUIBundle({{
                spec: JSON.parse({self.dumped_schema}),
                dom_id: '#swagger-container',
                layout: 'BaseLayout',
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
            }})
            </script>
          </body>
        """
        return f"""
        <!DOCTYPE html>
            <html>
                {head}
                {body}
            </html>
        """

    @get(media_type=MediaType.HTML, include_in_schema=False)
    def redoc(self, request: Request) -> str:  # pragma: no cover
        """Endpoint that serves Redoc"""
        schema = self.schema_from_request(request)
        if self.dumped_schema == "":
            self.dumped_schema = dumps(schema.json(by_alias=True, exclude_none=True), option=OPT_INDENT_2).decode(
                "utf-8"
            )
        head = f"""
          <head>
            <title>{schema.info.title}</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <script src="https://cdn.jsdelivr.net/npm/redoc@{self.redoc_version}/bundles/redoc.standalone.js"></script>
            <style>
                {self.styles}
            </style>
          </head>
        """
        body = f"""
          <body>
            <div id='redoc-container'/>
            <script type="text/javascript">
                Redoc.init(
                    JSON.parse({self.dumped_schema}),
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
        """
