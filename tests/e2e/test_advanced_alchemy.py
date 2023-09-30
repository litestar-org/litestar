from litestar import get
from litestar.contrib.sqlalchemy.plugins import SQLAlchemyInitPlugin, SQLAlchemySyncConfig
from litestar.repository.filters import LimitOffset
from litestar.testing import create_test_client


def test_using_pagination() -> None:
    # https://github.com/litestar-org/litestar/issues/2358
    async def provide_limit_offset_pagination() -> LimitOffset:
        return LimitOffset(limit=0, offset=0)

    @get(
        path="/",
        dependencies={"limit_offset": provide_limit_offset_pagination},
    )
    async def handler(limit_offset: LimitOffset) -> None:
        return None

    with create_test_client(
        route_handlers=[handler],
        plugins=[SQLAlchemyInitPlugin(SQLAlchemySyncConfig(connection_string="sqlite:///"))],
    ) as client:
        assert client.get("/").status_code == 200
