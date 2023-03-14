from http import HTTPStatus
from pathlib import Path

import pytest
from pydantic import BaseModel

from starlite import MediaType, Response, Starlite, get
from starlite._openapi.datastructures import ResponseSpec
from starlite._openapi.enums import OpenAPIType
from starlite._openapi.responses import (
    create_additional_responses,
    create_error_responses,
    create_responses,
    create_success_response,
)
from starlite.datastructures import Cookie, ResponseHeader
from starlite.exceptions import (
    HTTPException,
    PermissionDeniedException,
    ValidationException,
)
from starlite.response.base import T
from starlite.response_containers import File, Redirect, Stream, Template
from starlite.status_codes import (
    HTTP_200_OK,
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_406_NOT_ACCEPTABLE,
)
from tests import Person, PersonFactory
from tests.openapi.utils import PersonController, PetController, PetException


def test_create_responses() -> None:
    for route in Starlite(route_handlers=[PersonController]).routes:
        for route_handler, _ in route.route_handler_map.values():  # type: ignore
            if route_handler.include_in_schema:
                responses = create_responses(
                    route_handler=route_handler,
                    raises_validation_error=True,
                    generate_examples=True,
                    plugins=[],
                )
                assert responses
                assert str(route_handler.status_code) in responses
                assert str(HTTP_400_BAD_REQUEST) in responses

    responses = create_responses(
        route_handler=PetController.get_pets_or_owners,
        raises_validation_error=False,
        generate_examples=True,
        plugins=[],
    )
    assert responses
    assert str(HTTP_400_BAD_REQUEST) not in responses
    assert str(HTTP_406_NOT_ACCEPTABLE) in responses
    assert str(HTTP_200_OK) in responses


def test_create_error_responses() -> None:
    class AlternativePetException(HTTPException):
        status_code = ValidationException.status_code

    pet_exc_response, permission_denied_exc_response, validation_exc_response = tuple(
        create_error_responses(
            exceptions=[
                PetException,
                PermissionDeniedException,
                AlternativePetException,
                ValidationException,
            ]
        )
    )
    assert pet_exc_response[0] == str(PetException.status_code)
    assert pet_exc_response[1].description == HTTPStatus(PetException.status_code).description
    assert pet_exc_response[1].content[MediaType.JSON]  # type: ignore
    pet_exc_response_schema = pet_exc_response[1].content[MediaType.JSON].media_type_schema  # type: ignore
    assert pet_exc_response_schema.examples  # type: ignore
    assert pet_exc_response_schema.properties  # type: ignore
    assert pet_exc_response_schema.description  # type: ignore
    assert pet_exc_response_schema.required  # type: ignore
    assert pet_exc_response_schema.type  # type: ignore
    assert not pet_exc_response_schema.oneOf  # type: ignore

    assert permission_denied_exc_response[0] == str(PermissionDeniedException.status_code)
    assert (
        permission_denied_exc_response[1].description == HTTPStatus(PermissionDeniedException.status_code).description
    )
    assert permission_denied_exc_response[1].content[MediaType.JSON]  # type: ignore
    media_type_schema = permission_denied_exc_response[1].content[MediaType.JSON].media_type_schema  # type: ignore
    assert media_type_schema.examples  # type: ignore
    assert media_type_schema.properties  # type: ignore
    assert media_type_schema.description  # type: ignore
    assert media_type_schema.required  # type: ignore
    assert media_type_schema.type  # type: ignore
    assert not media_type_schema.oneOf  # type: ignore

    assert validation_exc_response[0] == str(ValidationException.status_code)
    assert validation_exc_response[1].description == HTTPStatus(ValidationException.status_code).description
    assert validation_exc_response[1].content[MediaType.JSON]  # type: ignore
    media_type_schema = validation_exc_response[1].content[MediaType.JSON].media_type_schema  # type: ignore
    assert media_type_schema.oneOf  # type: ignore
    assert len(media_type_schema.oneOf) == 2  # type: ignore
    for schema in media_type_schema.oneOf:  # type: ignore
        assert schema.examples  # type: ignore
        assert schema.description
        assert schema.properties  # type: ignore
        assert schema.required  # type: ignore
        assert schema.type  # type: ignore


def test_create_success_response_with_headers() -> None:
    @get(
        path="/test",
        response_headers=[ResponseHeader(name="special-header", value="100", description="super-duper special")],
        response_description="test",
        content_encoding="base64",
        content_media_type="image/png",
    )
    def handler() -> list:
        return []

    response = create_success_response(handler, True, plugins=[])
    assert response.description == "test"
    assert response.content[handler.media_type.value].media_type_schema.contentEncoding == "base64"  # type: ignore
    assert response.content[handler.media_type.value].media_type_schema.contentMediaType == "image/png"  # type: ignore
    assert response.headers["special-header"].param_schema.type == OpenAPIType.STRING  # type: ignore
    assert response.headers["special-header"].description == "super-duper special"  # type: ignore


def test_create_success_response_with_cookies() -> None:
    @get(
        path="/test",
        response_cookies=[
            Cookie(key="first-cookie", httponly=True, samesite="strict", description="the first cookie", secure=True),
            Cookie(key="second-cookie", max_age=500, description="the second cookie"),
        ],
    )
    def handler() -> list:
        return []

    response = create_success_response(handler, True, plugins=[])
    assert response.headers["Set-Cookie"].param_schema.dict(exclude_none=True) == {  # type: ignore
        "allOf": [
            {
                "description": "the first cookie",
                "example": 'first-cookie="<string>"; HttpOnly; Path=/; SameSite=strict; Secure',
            },
            {
                "description": "the second cookie",
                "example": 'second-cookie="<string>"; Max-Age=500; Path=/; SameSite=lax',
            },
        ]
    }


def test_create_success_response_with_response_class() -> None:
    @get(path="/test")
    def handler() -> Response[Person]:
        return Response(content=PersonFactory.build())

    response = create_success_response(handler, True, plugins=[])
    assert response.content["application/json"].media_type_schema.schema_class is Person  # type: ignore


def test_create_success_response_with_stream() -> None:
    @get(path="/test")
    def handler() -> Stream:
        return Stream(iterator=iter([]))

    response = create_success_response(handler, True, plugins=[])
    assert response.description == "Stream Response"


def test_create_success_response_redirect() -> None:
    @get(path="/test", status_code=HTTP_307_TEMPORARY_REDIRECT)
    def redirect_handler() -> Redirect:
        return Redirect(path="/target")

    response = create_success_response(redirect_handler, True, plugins=[])
    assert response.description == "Redirect Response"
    assert response.headers["location"].param_schema.type == OpenAPIType.STRING  # type: ignore
    assert response.headers["location"].description  # type: ignore


def test_create_success_response_file_data() -> None:
    @get(path="/test")
    def file_handler() -> File:
        return File(path=Path("test_responses.py"))

    response = create_success_response(file_handler, True, plugins=[])
    assert response.description == "File Download"
    assert response.headers["content-length"].param_schema.type == OpenAPIType.STRING  # type: ignore
    assert response.headers["content-length"].description  # type: ignore
    assert response.headers["last-modified"].param_schema.type == OpenAPIType.STRING  # type: ignore
    assert response.headers["last-modified"].description  # type: ignore
    assert response.headers["etag"].param_schema.type == OpenAPIType.STRING  # type: ignore
    assert response.headers["etag"].description  # type: ignore


def test_create_success_response_template() -> None:
    @get(path="/template")
    def template_handler() -> Template:
        return Template(name="none")

    response = create_success_response(template_handler, True, plugins=[])
    assert response.description == "Request fulfilled, document follows"
    assert response.content[MediaType.HTML]  # type: ignore


def test_create_additional_responses() -> None:
    class ServerError(BaseModel):
        pass

    class AuthenticationError(BaseModel):
        pass

    @get(
        responses={
            401: ResponseSpec(model=AuthenticationError, description="Authentication error"),
            500: ResponseSpec(model=ServerError, generate_examples=False, media_type=MediaType.TEXT),
        }
    )
    def handler() -> Person:
        return PersonFactory.build()

    responses = create_additional_responses(handler, plugins=[])

    first_response = next(responses)
    assert first_response[0] == "401"
    assert first_response[1].description == "Authentication error"
    media_type_schema = first_response[1].content["application/json"].media_type_schema  # type: ignore
    assert media_type_schema.schema_class is AuthenticationError  # type: ignore
    assert media_type_schema.examples  # type: ignore

    second_response = next(responses)
    assert second_response[0] == "500"
    assert second_response[1].description == "Additional response"
    media_type_schema = second_response[1].content["text/plain"].media_type_schema  # type: ignore
    assert media_type_schema.schema_class is ServerError  # type: ignore
    assert not media_type_schema.examples  # type: ignore

    with pytest.raises(StopIteration):
        next(responses)


def test_additional_responses_overlap_with_other_responses() -> None:
    class OkResponse(BaseModel):
        pass

    @get(responses={200: ResponseSpec(model=OkResponse, description="Overwritten response")})
    def handler() -> Person:
        return PersonFactory.build()

    responses = create_responses(handler, raises_validation_error=True, generate_examples=False, plugins=[])

    assert responses is not None
    assert responses["200"] is not None
    assert responses["200"].description == "Overwritten response"


def test_additional_responses_overlap_with_raises() -> None:
    class ErrorResponse(BaseModel):
        pass

    @get(
        raises=[ValidationException],
        responses={400: ResponseSpec(model=ErrorResponse, description="Overwritten response")},
    )
    def handler() -> Person:
        raise ValidationException()

    responses = create_responses(handler, raises_validation_error=True, generate_examples=False, plugins=[])

    assert responses is not None
    assert responses["400"] is not None
    assert responses["400"].description == "Overwritten response"


def test_create_response_for_response_subclass() -> None:
    class CustomResponse(Response[T]):
        pass

    @get(path="/test")
    def handler() -> CustomResponse[Person]:
        return CustomResponse(content=PersonFactory.build())

    response = create_success_response(handler, True, plugins=[])
    assert response.content["application/json"].media_type_schema.schema_class is Person  # type: ignore
