from litestar.openapi.plugins import StoplightRenderPlugin

stoplight_plugin = StoplightRenderPlugin(version="7.7.18", js_url=None, css_url=None, path="/elements")
