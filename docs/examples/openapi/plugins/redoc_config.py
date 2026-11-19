from litestar.openapi.plugins import RedocRenderPlugin

redoc_plugin = RedocRenderPlugin(
    version="v3.1.0",
    google_fonts=True,
    path="/redoc",
    js_url="https://cdn.company.internal/redoc/custom-redoc.js",
)
