from http import HTTPStatus

from starlette.status import (
    HTTP_200_OK,
    HTTP_307_TEMPORARY_REDIRECT,
    HTTP_400_BAD_REQUEST,
    HTTP_406_NOT_ACCEPTABLE,
)

from starlite import (
    File,
    MediaType,
    Redirect,
    Response,
    Starlite,
    Stream,
    Template,
    get,
)
from starlite.exceptions import (
    HTTPException,
    PermissionDeniedException,
    ValidationException,
)
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.responses import (
    create_error_responses,
    create_responses,
    create_success_response,
)
from starlite.types import ResponseHeader
from tests import Person
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
        response_headers={"special-header": ResponseHeader(value=100, description="super-duper special")},
        response_description="test",
        content_encoding="base64",
        content_media_type="image/png",
    )
    def handler() -> list:
        pass

    response = create_success_response(handler, True, plugins=[])
    assert response.description == "test"
    assert response.content[handler.media_type.value].media_type_schema.contentEncoding == "base64"  # type: ignore
    assert response.content[handler.media_type.value].media_type_schema.contentMediaType == "image/png"  # type: ignore
    assert response.headers["special-header"].param_schema.type == OpenAPIType.INTEGER  # type: ignore
    assert response.headers["special-header"].description == "super-duper special"  # type: ignore


def test_create_success_response_with_response_class() -> None:
    @get(path="/test")
    def handler() -> Response[Person]:
        pass

    response = create_success_response(handler, True, plugins=[])
    assert response.content["application/json"].media_type_schema.schema_class is Person  # type: ignore


def test_create_success_response_with_stream() -> None:
    @get(path="/test")
    def handler() -> Stream:
        pass

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
        ...

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
        ...

    response = create_success_response(template_handler, True, plugins=[])
    assert response.description == "Request fulfilled, document follows"
    assert response.content[MediaType.HTML]  # type: ignore
