from typing import Any, Optional, Type

import pytest
from pydantic import BaseConfig
from pydantic.fields import FieldInfo, ModelField

from starlite import HttpMethod, RequestEncodingType, create_test_request
from starlite.request import Request, get_model_kwargs_from_connection, get_request_data
from tests import Person, PersonFactory


class Config(BaseConfig):
    arbitrary_types_allowed = True


def create_model_field(
    field_name: str, field_type: Type[Any] = dict, field_info: Optional[FieldInfo] = None
) -> ModelField:
    return ModelField(
        name=field_name, type_=field_type, model_config=Config, class_validators=[], field_info=field_info
    )


@pytest.mark.asyncio
async def test_get_model_kwargs_from_connection():
    person_instance = PersonFactory.build()
    fields = {
        **Person.__fields__,
        "data": create_model_field(field_name="data", field_type=Person),
        "headers": create_model_field(field_name="headers"),
        "query": create_model_field(field_name="headers"),
        "cookies": create_model_field(field_name="headers"),
        "request": create_model_field(field_name="request", field_type=Request),
    }
    request = create_test_request(
        content=person_instance,
        headers={"MyHeader": "xyz"},
        query={"user": "123"},
        cookie="abcdefg",
        http_method=HttpMethod.POST,
    )
    result = await get_model_kwargs_from_connection(connection=request, fields=fields)
    assert result["data"]
    assert result["headers"]
    assert result["request"]
    assert result["query"]
    assert result["cookies"]


@pytest.mark.asyncio
@pytest.mark.parametrize("media_type", list(RequestEncodingType))
async def test_get_request_data(media_type):
    request = create_test_request(
        content={"key": "test"},
        request_media_type=media_type,
        http_method=HttpMethod.POST,
    )
    field = create_model_field(field_name="data", field_info=FieldInfo(media_type=media_type))
    data = await get_request_data(request=request, field=field)
    assert data["key"] == "test"
