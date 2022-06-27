from typing import Any, Dict, List, Type

import pytest
from pydantic import BaseConfig, BaseModel
from starlette.datastructures import UploadFile
from starlette.status import HTTP_201_CREATED

from starlite import Body, RequestEncodingType, post
from starlite.testing import create_test_client
from tests import Person, PersonFactory
from tests.kwargs import Form


class FormData(BaseModel):
    name: UploadFile
    age: UploadFile
    programmer: UploadFile

    class Config:
        arbitrary_types_allowed = True


@pytest.mark.parametrize("t_type", [FormData, Dict[str, UploadFile], List[UploadFile], UploadFile])
def test_request_body_multi_part(t_type: Type[Any]) -> None:

    body = Body(media_type=RequestEncodingType.MULTI_PART)

    test_path = "/test"
    data = Form(name="Moishe Zuchmir", age=30, programmer=True).dict()

    @post(path=test_path)
    def test_method(data: t_type = body) -> None:  # type: ignore
        assert data

    with create_test_client(test_method) as client:
        response = client.post(test_path, files=data)
        assert response.status_code == HTTP_201_CREATED


def test_request_body_multi_part_mixed_field_content_types() -> None:
    person = PersonFactory.build()

    class MultiPartFormWithMixedFields(BaseModel):
        class Config(BaseConfig):
            arbitrary_types_allowed = True

        image: UploadFile
        tags: List[str]
        profile: Person

    @post(path="/")
    async def test_method(data: MultiPartFormWithMixedFields = Body(media_type=RequestEncodingType.MULTI_PART)) -> None:
        assert await data.image.read() == b"data"
        assert data.tags == ["1", "2", "3"]
        assert data.profile == person

    with create_test_client(test_method) as client:
        response = client.post(
            "/",
            files={"image": ("image.png", b"data")},
            data=[("tags", "1"), ("tags", "2"), ("tags", "3"), ("profile", person.json())],
        )
        assert response.status_code == HTTP_201_CREATED
