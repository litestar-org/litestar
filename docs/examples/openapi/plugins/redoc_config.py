from litestar.openapi.plugins import RedocRenderPlugin

redoc_plugin = RedocRenderPlugin(version="next", js_url=None, google_fonts=True, path="/redoc")
