import pytest

from starlite import ImproperlyConfiguredException, MediaType, Response
from tests.utils import PersonFactory, PydanticDataClassPerson, VanillaDataClassPerson


@pytest.mark.parametrize(
    "content, media_type",
    [
        [PersonFactory.build(), MediaType.JSON],
        [VanillaDataClassPerson(**PersonFactory.build().dict()), MediaType.JSON],
        [PydanticDataClassPerson(**PersonFactory.build().dict()), MediaType.JSON],
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
def test_response_serialization(content, media_type):
    response = Response(content=content, media_type=media_type)
    assert response.body


def test_response_error_handling():
    with pytest.raises(ImproperlyConfiguredException):
        Response(content={}, media_type=MediaType.TEXT)
