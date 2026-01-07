from litestar.openapi.plugins import ScalarRenderPlugin

scalar_plugin = ScalarRenderPlugin(version="1.19.5", path="/scalar")

# Example demonstrating custom Scalar render options
# For more configuration options, see: https://guides.scalar.com/scalar/scalar-api-references/configuration
scalar_plugin_with_options = ScalarRenderPlugin(
    options={
        # Hide the sidebar to give more space to the main content
        "showSidebar": False
    }
)
