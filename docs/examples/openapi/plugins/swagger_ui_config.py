from litestar.openapi.plugins import SwaggerRenderPlugin

swagger_plugin = SwaggerRenderPlugin(
    version="5.1.3", js_url=None, css_url=None, standalone_preset_js_url=None, init_oauth=None, path="/swagger"
)
