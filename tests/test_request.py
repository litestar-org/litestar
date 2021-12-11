from asyncio import sleep
from typing import Any, cast

import pytest
from pydantic import BaseConfig
from pydantic.fields import ModelField
from starlette.requests import Request

from starlite import HttpMethod, route
from starlite.request import get_kwargs_from_request, handle_request, parse_query_params
from starlite.testing import create_test_request
from tests.utils import Person, PersonFactory


def test_parse_query_params():
    query = {
        "value": 10,
        "veggies": ["tomato", "potato", "aubergine"],
        "calories": 122.53,
        "healthy": True,
        "polluting": False,
    }
    request = create_test_request(query=query)
    result = parse_query_params(request=request)
    assert result == query


@pytest.mark.asyncio
async def test_get_kwargs_from_request():
    class Config(BaseConfig):
        arbitrary_types_allowed = True

    person_instance = PersonFactory.build()
    fields = {
        **Person.__fields__,
        "data": ModelField(name="data", type_=Person, class_validators=[], model_config=Config),
        "headers": ModelField(name="headers", type_=dict, class_validators=[], model_config=Config),
        "request": ModelField(name="request", type_=Request, class_validators=[], model_config=Config),
    }
    request = create_test_request(
        content=person_instance, headers={"MyHeader": "xyz"}, query={"user": "123"}, http_method=HttpMethod.POST
    )
    result = await get_kwargs_from_request(request=request, fields=fields)
    assert result["data"]
    assert result["headers"]
    assert result["request"]


@pytest.mark.asyncio
async def test_handle_request():
    @route(http_method=HttpMethod.POST, path="/person")
    async def test_function(data: Person):
        assert isinstance(data, Person)
        await sleep(0.1)
        return data

    person_instance = PersonFactory.build()
    request = create_test_request(content=person_instance, http_method=HttpMethod.POST)

    response = await handle_request(route_handler=cast(Any, test_function), request=request)
    assert response.body.decode("utf-8") == person_instance.json()
