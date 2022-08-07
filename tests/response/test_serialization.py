from json import loads
from typing import Any, Dict, List

import pytest
from starlette.status import HTTP_200_OK

from starlite import MediaType, Response
from tests import Person, PersonFactory, PydanticDataClassPerson, VanillaDataClassPerson

person = PersonFactory.build()


@pytest.mark.parametrize(
    "content, response_type, media_type",
    [
        [person, Person, MediaType.JSON],
        [{"key": 123}, Dict[str, int], MediaType.JSON],
        [[{"key": 123}], List[Dict[str, int]], MediaType.JSON],
        [VanillaDataClassPerson(**person.dict()), VanillaDataClassPerson, MediaType.JSON],
        [PydanticDataClassPerson(**person.dict()), PydanticDataClassPerson, MediaType.JSON],
        ["abcdefg", str, MediaType.TEXT],
        ["<div/>", str, MediaType.HTML],
    ],
)
def test_response_serialization(content: Any, response_type: Any, media_type: MediaType) -> None:
    response = Response[response_type](content, media_type=media_type, status_code=HTTP_200_OK)  # type: ignore[valid-type]
    if media_type == MediaType.JSON:
        value = loads(response.body)
        if isinstance(value, dict):
            assert content.__class__(**value) == content
        else:
            assert [content[0].__class__(**value[0])] == content
    else:
        assert response.body == content.encode("utf-8")
