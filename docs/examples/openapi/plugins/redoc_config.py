from litestar.openapi.plugins import RedocRenderPlugin

redoc_plugin = RedocRenderPlugin(
    version="latest",
    google_fonts=True,
    path="/redoc",
    js_url="https://cdn.company.internal/redoc/custom-redoc.js",
)
