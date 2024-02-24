from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from litestar.connection import Request
from litestar.openapi.plugins import OpenAPIRenderPlugin


class RapidocRenderPlugin(OpenAPIRenderPlugin):
    """Render an OpenAPI schema using Rapidoc."""

    def __init__(
        self,
        *,
        version: str = "9.3.4",
        js_url: str | None = None,
        path: str | Sequence[str] = "/rapidoc",
        **kwargs: Any,
    ) -> None:
        """Initialize the OpenAPI UI render plugin.

        Args:
            version: Rapidoc version to download from the CDN. If js_url is provided, this is ignored.
            js_url: Download url for the RapiDoc JS bundle. If not provided, the version will be used to construct the
                url.
            path: Path to serve the OpenAPI UI at.
            **kwargs: Additional arguments to pass to the base class.
        """
        self.js_url = js_url or f"https://unpkg.com/rapidoc@{version}/dist/rapidoc-min.js"
        super().__init__(path=path, **kwargs)

    def render(self, request: Request, openapi_schema: dict[str, Any]) -> bytes:
        """Render an HTML page for Rapidoc.

        Notes:
            - override this method to customize the template.

        Args:
            request: The request.
            openapi_schema: The OpenAPI schema as a dictionary.

        Returns:
            A rendered html string.
        """

        head = f"""
          <head>
            <title>{openapi_schema["info"]["title"]}</title>
            {self.favicon}
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <script src="{self.js_url}" crossorigin></script>
            {self.style}
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
