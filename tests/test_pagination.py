from itertools import islice
from typing import List, Optional, Tuple

from starlite import (
    AbstractCursorPaginator,
    AbstractLimitOffsetPaginator,
    CursorPagination,
    LimitOffsetPagination,
    create_test_client,
    get,
)
from starlite.app import DEFAULT_OPENAPI_CONFIG
from starlite.status_codes import HTTP_200_OK
from tests import Person, PersonFactory


class TestIndexOffsetPaginator(AbstractLimitOffsetPaginator[Person]):
    def __init__(self, data: List[Person]):

        self.data = data

    async def get_total(self) -> int:
        return len(self.data)

    async def get_items(self, limit: int, offset: int) -> List[Person]:
        return list(islice(islice(self.data, offset, None), limit))


data = PersonFactory.batch(50)


def test_limit_offset_pagination_data_shape() -> None:
    @get("/")
    async def handler(limit: int, offset: int) -> LimitOffsetPagination[Person]:
        return await TestIndexOffsetPaginator(data=data).get_paginated_data(limit=limit, offset=offset)

    with create_test_client(handler) as client:
        response = client.get("/", params={"limit": 5, "offset": 0})
        assert response.status_code == HTTP_200_OK

        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["total"] == 50
        assert response_data["limit"] == 5
        assert response_data["offset"] == 0


def test_limit_offset_pagination_openapi_schema() -> None:
    @get("/")
    async def handler(limit: int, offset: int) -> LimitOffsetPagination[Person]:
        return await TestIndexOffsetPaginator(data=data).get_paginated_data(limit=limit, offset=offset)

    with create_test_client(handler, openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        schema = client.app.openapi_schema
        assert schema

        spec = schema.dict(exclude_none=True)["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]
        assert spec == {
            "media_type_schema": {
                "properties": {
                    "items": {"items": {"ref": "#/components/schemas/Person"}, "type": "array"},
                    "limit": {"type": "integer", "description": "Maximal number of items to send."},
                    "offset": {"type": "integer", "description": "Offset from the beginning of the query."},
                    "total": {"type": "integer", "description": "Total number of items."},
                },
                "type": "object",
            }
        }


class TestCursorPagination(AbstractCursorPaginator[str, Person]):
    def __init__(self, data: List[Person]):
        self.data = data

    async def get_items(self, cursor: Optional[str], results_per_page: int) -> "Tuple[List[Person], Optional[str]]":
        results = self.data[:results_per_page]
        return results, results[-1].id


def test_cursor_pagination_data_shape() -> None:
    @get("/")
    async def handler(cursor: Optional[str] = None) -> CursorPagination[str, Person]:
        return await TestCursorPagination(data=data).get_paginated_data(cursor=cursor, results_per_page=5)

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK

        response_data = response.json()
        assert len(response_data["items"]) == 5
        assert response_data["results_per_page"] == 5
        assert response_data["cursor"] == data[4].id


def test_cursor_pagination_openapi_schema() -> None:
    @get("/")
    async def handler(cursor: Optional[str] = None) -> CursorPagination[str, Person]:
        return await TestCursorPagination(data=data).get_paginated_data(cursor=cursor, results_per_page=5)

    with create_test_client(handler, openapi_config=DEFAULT_OPENAPI_CONFIG) as client:
        schema = client.app.openapi_schema
        assert schema

        spec = schema.dict(exclude_none=True)["paths"]["/"]["get"]["responses"]["200"]["content"]["application/json"]
        assert spec == {
            "media_type_schema": {
                "properties": {
                    "items": {"items": {"ref": "#/components/schemas/Person"}, "type": "array"},
                    "cursor": {
                        "type": "string",
                        "description": "Unique ID, designating the last identifier in the given data set. This value can be used to request the 'next' batch of records.",
                    },
                    "results_per_page": {"type": "integer", "description": "Maximal number of items to send."},
                },
                "type": "object",
            }
        }
