from http import HTTPStatus

from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_406_NOT_ACCEPTABLE

from starlite import FileData, HttpMethod, MediaType, Starlite, get, redirect
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
from tests.openapi.utils import PersonController, PetController, PetException


def test_create_responses():
    for route in Starlite(route_handlers=[PersonController]).router.routes:
        for route_handler in route.route_handler_map.values():
            if route_handler.include_in_schema:
                responses = create_responses(
                    route_handler=route_handler,
                    raises_validation_error=True,
                    default_response_headers=None,
                    generate_examples=True,
                )
                assert str(route_handler.status_code) in responses
                assert str(HTTP_400_BAD_REQUEST) in responses

    responses = create_responses(
        route_handler=PetController.get_pets_or_owners,
        raises_validation_error=False,
        default_response_headers=None,
        generate_examples=True,
    )
    assert str(HTTP_400_BAD_REQUEST) not in responses
    assert str(HTTP_406_NOT_ACCEPTABLE) in responses
    assert str(HTTP_200_OK) in responses
    response = responses[str(HTTP_200_OK)]
    assert response.headers["application-type"].param_schema.type == OpenAPIType.STRING
    assert response.headers["Access-Control-Allow-Origin"].param_schema.type == OpenAPIType.STRING
    assert response.headers["x-my-tag"].param_schema.type == OpenAPIType.STRING
    assert not response.headers["omitted-tag"].param_schema.required


def test_create_error_responses():
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
    assert pet_exc_response[1].content[MediaType.JSON]
    pet_exc_response_schema = pet_exc_response[1].content[MediaType.JSON].media_type_schema
    assert pet_exc_response_schema.examples
    assert pet_exc_response_schema.properties
    assert pet_exc_response_schema.description
    assert pet_exc_response_schema.required
    assert pet_exc_response_schema.type
    assert not pet_exc_response_schema.oneOf

    assert permission_denied_exc_response[0] == str(PermissionDeniedException.status_code)
    assert (
        permission_denied_exc_response[1].description == HTTPStatus(PermissionDeniedException.status_code).description
    )
    assert permission_denied_exc_response[1].content[MediaType.JSON]
    permission_denied_exc_response = permission_denied_exc_response[1].content[MediaType.JSON].media_type_schema
    assert permission_denied_exc_response.examples
    assert permission_denied_exc_response.properties
    assert permission_denied_exc_response.description
    assert permission_denied_exc_response.required
    assert permission_denied_exc_response.type
    assert not permission_denied_exc_response.oneOf

    assert validation_exc_response[0] == str(ValidationException.status_code)
    assert validation_exc_response[1].description == HTTPStatus(ValidationException.status_code).description
    assert validation_exc_response[1].content[MediaType.JSON]
    validation_exc_response = validation_exc_response[1].content[MediaType.JSON].media_type_schema
    assert validation_exc_response.oneOf
    assert len(validation_exc_response.oneOf) == 2
    for schema in validation_exc_response.oneOf:
        assert schema.examples
        assert schema.description
        assert schema.properties
        assert schema.required
        assert schema.type


def test_create_success_response():
    @redirect(path="/test", http_method=[HttpMethod.GET, HttpMethod.POST])
    def redirect_handler() -> str:
        return "/target"

    response = create_success_response(redirect_handler, None, True)
    assert response.description == "Redirect Response"
    assert response.headers["location"].param_schema.type == OpenAPIType.STRING
    assert response.headers["location"].description

    @get(path="/test")
    def file_handler() -> FileData:
        ...

    response = create_success_response(file_handler, None, True)
    assert response.description == "File Download"
