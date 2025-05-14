from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

app = Litestar(
    openapi_config=OpenAPIConfig(
        title="My API",
        version="0.1.0",
        create_examples=True,
    ),
)
