from typing import List, Optional

import pytest
from pydantic import BaseModel, Field
from pydantic_factories import ModelFactory
from starlette.status import HTTP_200_OK

from starlite import Controller
from starlite.decorators import get


class Person(BaseModel):
    id: int
    first_name: str
    last_name: str


class QueryParams(BaseModel):
    first: str
    second: List[str] = Field(min_items=3)
    third: Optional[int]


class PersonFactory(ModelFactory):
    __model__ = Person


class QueryParamsFactory(ModelFactory):
    __model__ = QueryParams


person_instance = PersonFactory.build()


@pytest.mark.asyncio
def test_controller_get(create_test_client):
    path = "/person"

    class MyController(Controller):
        response_model = Person

        @get(url=path)
        def get_method(self, **kwargs):
            return person_instance

    controller = MyController()

    with create_test_client(controller.routes) as client:
        response = client.get(path)
        assert response.status_code == HTTP_200_OK
        assert response.json() == person_instance.dict()


# @pytest.mark.asyncio
# def test_path_params(create_test_client):
#     path = "/person/{person_id:int}"
#
#     class View(Controller):
#         response_model = Person
#
#         def get(self, person_id: int, **kwargs):
#             assert person_id == person_instance.id
#             return person_instance
#
#     route = RouteConfig(path, View)
#
#     with create_test_client(route) as client:
#         response = client.get(f"/person/{person_instance.id}")
#         assert response.status_code == HTTP_200_OK
#
#
# @pytest.mark.asyncio
# def test_query_params(create_test_client):
#     path = "/person"
#
#     query_params_instance = QueryParamsFactory.build()
#
#     class View(Controller):
#         response_model = Person
#         query_model = QueryParams
#
#         async def get(
#             self, first: str, second: List[str], third: Optional[int] = None, **kwargs
#         ):
#             assert first == query_params_instance.first
#             assert second == query_params_instance.second
#             assert third == query_params_instance.third
#             return person_instance
#
#     route = RouteConfig(path, View)
#
#     with create_test_client(route) as client:
#         response = client.get("/person", params=query_params_instance.dict())
#         assert response.status_code == HTTP_200_OK
#
#
# @pytest.mark.asyncio
# def test_config_status_code(create_test_client):
#     path = "/person"
#
#     class View(Controller):
#         response_model = Person
#         query_params_model = QueryParams
#
#         @route(status_code=HTTP_201_CREATED)
#         def get(self, **kwargs):
#             return person_instance
#
#     route = RouteConfig(path, View)
#
#     with create_test_client(route) as client:
#         response = client.get("/person")
#         assert response.status_code == HTTP_201_CREATED
