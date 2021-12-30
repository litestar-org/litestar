from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode
from uuid import uuid1, uuid4

import pytest
from pydantic import UUID4, BaseModel
from pydantic.fields import FieldInfo
from starlette.datastructures import UploadFile
from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from typing_extensions import Type

from starlite import (
    Body,
    ImproperlyConfiguredException,
    Parameter,
    RequestEncodingType,
    Starlite,
    create_test_client,
    get,
    post,
)


@pytest.mark.parametrize(
    "params_dict,should_raise",
    [
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok", "Polgat"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 101,
                "brands": ["Nike", "Adidas", "Rebok"],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": [],
            },
            True,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
            },
            False,
        ),
        (
            {
                "page": 1,
                "pageSize": 1,
                "brands": ["Nike", "Adidas", "Rebok"],
                "from_date": datetime.now().timestamp(),
                "to_date": datetime.now().timestamp(),
            },
            False,
        ),
    ],
)
def test_query_params(params_dict: dict, should_raise: bool):
    test_path = "/test"

    @get(path=test_path)
    def test_method(
        page: int,
        page_size: int = Parameter(query="pageSize", gt=0, le=100),
        brands: List[str] = Parameter(min_items=1, max_items=3),
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> None:
        assert page
        assert page_size
        assert brands
        assert from_date or from_date is None
        assert to_date or to_date is None

    with create_test_client(test_method) as client:
        response = client.get(f"{test_path}?{urlencode(params_dict, doseq=True)}")
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize(
    "params_dict,should_raise",
    [
        (
            {
                "version": 1.0,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            False,
        ),
        (
            {
                "version": 4.1,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 101,
                "user_id": "abc",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 1,
                "user_id": "abcdefghijklm",
                "order_id": str(uuid4()),
            },
            True,
        ),
        (
            {
                "version": 0.2,
                "service_id": 1,
                "user_id": "abc",
                "order_id": str(uuid1()),
            },
            True,
        ),
    ],
)
def test_path_params(params_dict: dict, should_raise: bool):
    test_path = "{version:float}/{service_id:int}/{user_id:str}/{order_id:uuid}"

    @get(path=test_path)
    def test_method(
        order_id: UUID4,
        version: float = Parameter(gt=0.1, le=4.0),
        service_id: int = Parameter(gt=0, le=100),
        user_id: str = Parameter(min_length=1, max_length=10),
    ) -> None:
        assert version
        assert service_id
        assert user_id
        assert order_id

    with create_test_client(test_method) as client:
        response = client.get(
            f"{params_dict['version']}/{params_dict['service_id']}/{params_dict['user_id']}/{params_dict['order_id']}"
        )
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK


def test_path_param_validation():
    @get(path="/{param}")
    def test_method() -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        Starlite(route_handlers=[test_method])


@pytest.mark.parametrize(
    "t_type,param_dict, param, should_raise",
    [
        (str, {"special-header": "123"}, Parameter(header="special-header", min_length=1, max_length=3), False),
        (str, {"special-header": "123"}, Parameter(header="special-header", min_length=1, max_length=2), True),
        (str, {}, Parameter(header="special-header", min_length=1, max_length=2), True),
        (Optional[str], {}, Parameter(header="special-header", min_length=1, max_length=2, required=False), False),
        (int, {"special-header": "123"}, Parameter(header="special-header", ge=100, le=201), False),
        (int, {"special-header": "123"}, Parameter(header="special-header", ge=100, le=120), True),
        (int, {}, Parameter(header="special-header", ge=100, le=120), True),
        (Optional[int], {}, Parameter(header="special-header", ge=100, le=120, required=False), False),
    ],
)
def test_header_params(t_type: Type, param_dict: dict, param: FieldInfo, should_raise: bool):
    test_path = "/test"

    @get(path=test_path)
    def test_method(special_header: t_type = param) -> None:
        if special_header:
            assert special_header in [param_dict.get("special-header"), int(param_dict.get("special-header"))]

    with create_test_client(test_method) as client:
        response = client.get(test_path, headers=param_dict)
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK


@pytest.mark.parametrize(
    "t_type,param_dict, param, should_raise",
    [
        (str, {"special-cookie": "123"}, Parameter(cookie="special-cookie", min_length=1, max_length=3), False),
        (str, {"special-cookie": "123"}, Parameter(cookie="special-cookie", min_length=1, max_length=2), True),
        (str, {}, Parameter(cookie="special-cookie", min_length=1, max_length=2), True),
        (Optional[str], {}, Parameter(cookie="special-cookie", min_length=1, max_length=2, required=False), False),
        (int, {"special-cookie": "123"}, Parameter(cookie="special-cookie", ge=100, le=201), False),
        (int, {"special-cookie": "123"}, Parameter(cookie="special-cookie", ge=100, le=120), True),
        (int, {}, Parameter(cookie="special-cookie", ge=100, le=120), True),
        (Optional[int], {}, Parameter(cookie="special-cookie", ge=100, le=120, required=False), False),
    ],
)
def test_cookie_params(t_type: Type, param_dict: dict, param: FieldInfo, should_raise: bool):
    test_path = "/test"

    @get(path=test_path)
    def test_method(special_cookie: t_type = param) -> None:
        if special_cookie:
            assert special_cookie in [param_dict.get("special-cookie"), int(param_dict.get("special-cookie"))]

    with create_test_client(test_method) as client:
        response = client.get(test_path, cookies=param_dict)
        if should_raise:
            assert response.status_code == HTTP_400_BAD_REQUEST
        else:
            assert response.status_code == HTTP_200_OK


class Form(BaseModel):
    name: str
    age: int
    programmer: bool


def test_request_body_json():
    body = Body(media_type=RequestEncodingType.JSON)

    test_path = "/test"
    data = Form(name="Moishe Zuchmir", age=30, programmer=True).dict()

    @post(path=test_path)
    def test_method(data: Form = body) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post(test_path, json=data)
        assert response.status_code == HTTP_201_CREATED


def test_request_body_url_encoded():
    body = Body(media_type=RequestEncodingType.URL_ENCODED)

    test_path = "/test"
    data = Form(name="Moishe Zuchmir", age=30, programmer=True).dict()

    @post(path=test_path)
    def test_method(data: Form = body) -> None:
        assert isinstance(data, Form)

    with create_test_client(test_method) as client:
        response = client.post(test_path, data=data)
        assert response.status_code == HTTP_201_CREATED


class FormData(BaseModel):
    name: UploadFile
    age: UploadFile
    programmer: UploadFile

    class Config:
        arbitrary_types_allowed = True


@pytest.mark.parametrize("t_type", [FormData, Dict[str, UploadFile], List[UploadFile], UploadFile])
def test_request_body_multi_part(t_type: Type[Any]):

    body = Body(media_type=RequestEncodingType.MULTI_PART)

    test_path = "/test"
    data = Form(name="Moishe Zuchmir", age=30, programmer=True).dict()

    @post(path=test_path)
    def test_method(data: t_type = body) -> None:
        assert data

    with create_test_client(test_method) as client:
        response = client.post(test_path, files=data)
        assert response.status_code == HTTP_201_CREATED


@pytest.mark.xfail
def test_request_body_multi_part_mixed_field_content_types() -> None:
    class MultiPartFormWithMixedFields(BaseModel):
        # TODO: define an API for declaring the fields
        file: UploadFile
        tags: List[str]

    @post(path="/")
    async def test_method(data: MultiPartFormWithMixedFields = Body(media_type=RequestEncodingType.MULTI_PART)) -> None:
        assert await data.file.read() == b"file data"
        assert data.tags == ["1", "2"]

    with create_test_client(test_method) as client:
        response = client.post(
            "/",
            files=[
                ("file", ("somefile.txt", b"file data")),
                ("tags", (None, b"tags=1&tags=2", "application/x-www-form-urlencoded")),
            ],
        )
        assert response.status_code == HTTP_201_CREATED
