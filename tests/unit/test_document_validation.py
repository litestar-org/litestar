from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Components
from litestar.openapi.spec.security_scheme import SecurityScheme


def test_invalid_generated_document_is_reported(validate_generated_openapi_documents: list[str]) -> None:
    app = Litestar(
        openapi_config=OpenAPIConfig(
            title="test",
            version="1",
            components=Components(security_schemes={"broken": SecurityScheme(type="http")}),
        )
    )

    assert app.openapi_schema
    errors = list(validate_generated_openapi_documents)
    validate_generated_openapi_documents.clear()
    assert errors == ["'scheme' is a required property"]
