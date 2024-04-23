from litestar import Litestar, Request, get
from litestar.datastructures import ResponseHeader


@get("/")
async def hello_world1(request: Request) -> None:
    request.logger.info("inside request")
    return


app1 = Litestar(
    route_handlers=[hello_world1],
    response_headers=[ResponseHeader(name="X-Version", value="ABCD", description="Test")],
)


def test_included_header_fields() -> None:
    # https://github.com/litestar-org/litestar/issues/3416

    assert app1.openapi_schema.to_schema()["paths"]["/"]["get"]["responses"]["200"]["headers"] == {
        "X-Version": {
            "allowEmptyValue": False,
            "allowReserved": False,
            "deprecated": False,
            "description": "Test",
            "required": False,
            "schema": {"type": "string"},
        }
    }
