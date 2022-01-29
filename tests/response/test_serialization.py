from json import loads
from typing import Any

import pytest
from starlette.status import HTTP_200_OK

from starlite import MediaType, Response
from tests import PersonFactory, PydanticDataClassPerson, VanillaDataClassPerson


@pytest.mark.parametrize(
    "content, media_type",
    [
        [PersonFactory.build(), MediaType.JSON],
        [{"key": 123}, MediaType.JSON],
        [[{"key": 123}], MediaType.JSON],
        [VanillaDataClassPerson(**PersonFactory.build().dict()), MediaType.JSON],
        [PydanticDataClassPerson(**PersonFactory.build().dict()), MediaType.JSON],  # type: ignore
        [
            {
                "key": [{"nested": 1}],
            },
            MediaType.JSON,
        ],
        ["abcdefg", MediaType.TEXT],
        ["<div/>", MediaType.HTML],
    ],
)
def test_response_serialization(content: Any, media_type: MediaType):
    response = Response(content=content, media_type=media_type, status_code=HTTP_200_OK)
    if media_type == MediaType.JSON:
        value = loads(response.body)
        if isinstance(value, dict):
            assert content.__class__(**value) == content
        else:
            assert [content[0].__class__(**value[0])] == content
    else:
        assert response.body == content.encode("utf-8")
