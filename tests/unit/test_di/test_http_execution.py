import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated, Any

import pytest
from pytest_mock import MockerFixture

from litestar import Litestar, Request, get, post
from litestar.connection import ASGIConnection
from litestar.datastructures import UploadFile
from litestar.di import DIContext, NamedDependency, PreparedDIContext, Provide
from litestar.dto import AbstractDTO, DataclassDTO, DTOConfig, DTOData
from litestar.exceptions import (
    DTONotApplicableError,
    HTTPException,
    ImproperlyConfiguredException,
    ValidationException,
)
from litestar.params import Body, FromQuery, JSONBody, MultipartBody, QueryParameter
from litestar.plugins import SerializationPlugin
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from litestar.testing import AsyncTestClient, TestClient, create_test_client
from litestar.typing import FieldDefinition


def test_request_parameters_are_validated_before_any_dependency_runs() -> None:
    produced: list[str] = []

    async def provide_resource() -> AsyncGenerator[str, None]:
        produced.append("resource")
        yield "resource"

    @get("/", dependencies={"resource": Provide(provide_resource)})
    async def handler(resource: NamedDependency[str], page: FromQuery[int]) -> str:
        return resource

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        response = client.get("/?page=notanint")

    assert response.status_code == 400
    assert response.json()["extra"] == [{"message": "Expected `int`, got `str`", "key": "page", "source": "query"}]
    assert produced == []


def test_request_parameter_of_unused_dependency_is_not_validated() -> None:
    async def provide_limited(limit: FromQuery[int]) -> int:
        return limit

    @get("/")
    async def handler() -> str:
        return "ok"

    app = Litestar([handler], dependencies={"limited": Provide(provide_limited)}, openapi_config=None)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/?limit=notanint").status_code == 200


def test_handler_without_dependencies_gets_no_handler_context(mocker: MockerFixture) -> None:
    # tests a performance optimisation: a handler context is built only if something is resolved in it
    @get("/")
    async def handler() -> str:
        return "ok"

    enter = mocker.spy(DIContext, "__aenter__")
    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/").text == "ok"

    assert [context.scope for context in enter.spy_return_list] == ["app", "request"]


def test_handler_with_request_parameters_only_gets_no_handler_context(mocker: MockerFixture) -> None:
    # tests a performance optimisation: a handler context is built only if something is resolved in it
    @get("/")
    async def handler(page: FromQuery[int]) -> int:
        return page

    enter = mocker.spy(DIContext, "__aenter__")
    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/?page=2").text == "2"

    assert [context.scope for context in enter.spy_return_list] == ["app", "request"]


def test_handler_taking_request_gets_no_handler_context(mocker: MockerFixture) -> None:
    # tests a performance optimisation: a handler context is built only if something is resolved in it
    @get("/")
    async def handler(request: Request, page: FromQuery[int]) -> str:
        return f"{request.method} {page}"

    enter = mocker.spy(DIContext, "__aenter__")
    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/?page=2").text == "GET 2"

    assert [context.scope for context in enter.spy_return_list] == ["app", "request"]


def test_request_and_handler_context_created_without_scope_checks(mocker: MockerFixture) -> None:
    # tests a performance optimisation: the scopes of the request's and the handler's context are checked
    # once, when the handler's injection setup is created
    async def provide_value() -> int:
        return 1

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int]) -> int:
        return value

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        prepare = mocker.spy(PreparedDIContext, "__init__")
        enter = mocker.spy(DIContext, "__aenter__")
        assert client.get("/").text == "1"

    assert [context.scope for context in enter.spy_return_list] == ["request", "handler"]
    assert prepare.call_count == 0


def test_handler_takes_request_under_each_class_of_request_class() -> None:
    class CustomRequest(Request[Any, Any, Any]):
        pass

    @get("/")
    async def handler(custom: CustomRequest, request: Request, connection: ASGIConnection) -> bool:
        return custom is request is connection and type(custom) is CustomRequest

    with TestClient(Litestar([handler], request_class=CustomRequest, openapi_config=None)) as client:
        assert client.get("/").json() is True


def test_handler_and_dependency_take_same_request() -> None:
    async def provide_request_id(request: Request) -> int:
        return id(request)

    @get("/", dependencies={"request_id": Provide(provide_request_id)})
    async def handler(request: Request, request_id: NamedDependency[int]) -> bool:
        return id(request) == request_id

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        assert client.get("/").json() is True


def test_layer_parameter_nothing_declares_validated_for_handler_with_dependency() -> None:
    async def provide_value() -> int:
        return 1

    @get("/", dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int]) -> int:
        return value

    app = Litestar(
        [handler], parameters={"limit": QueryParameter(annotation=int, name="page-limit")}, openapi_config=None
    )
    with TestClient(app) as client:
        assert client.get("/?page-limit=5").text == "1"
        assert client.get("/?page-limit=notanint").status_code == 400


def test_generator_dependency_torn_down_with_failure_of_later_dependency_thrown_in() -> None:
    events: list[str] = []

    async def provide_resource() -> AsyncGenerator[str, None]:
        try:
            yield "resource"
        except Exception as exc:
            events.append(f"thrown in: {type(exc).__name__}")
            raise
        finally:
            events.append("torn down")

    async def provide_failing(resource: NamedDependency[str]) -> str:
        raise RuntimeError("production failed")

    @get("/", dependencies={"resource": Provide(provide_resource), "failing": Provide(provide_failing)})
    async def handler(failing: NamedDependency[str]) -> str:
        return failing

    with TestClient(Litestar([handler], openapi_config=None)) as client:
        response = client.get("/")

    assert response.status_code == 500
    assert events == ["thrown in: RuntimeError", "torn down"]


@pytest.mark.parametrize(
    "exception,status_code,text",
    [
        (ValueError("value_error"), HTTP_500_INTERNAL_SERVER_ERROR, "500 - Internal Server Error"),
        (
            HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="http_exception"),
            HTTP_422_UNPROCESSABLE_ENTITY,
            '{"status_code":422,"detail":"http_exception"}',
        ),
        (
            ValidationException("validation_exception"),
            HTTP_400_BAD_REQUEST,
            '{"status_code":400,"detail":"validation_exception"}',
        ),
    ],
)
def test_exception_raised_by_dependency_is_handled_like_exception_raised_by_handler(
    exception: Exception, status_code: int, text: str
) -> None:
    async def dummy() -> None:
        pass

    def a() -> None:
        raise exception

    def c(a: NamedDependency[None], b: NamedDependency[None]) -> None:
        pass

    @get(path="/")
    def handler(c: NamedDependency[None]) -> None:
        pass

    with create_test_client(
        route_handlers=handler,
        dependencies={
            "a": Provide(a, sync_to_thread=False),
            "b": Provide(dummy),
            "c": Provide(c, sync_to_thread=False),
        },
    ) as client:
        response = client.get("/")

    assert response.status_code == status_code
    assert text in response.text


async def test_independent_generator_dependencies_torn_down_one_after_the_other_most_recently_produced_first() -> None:
    events: list[str] = []
    second_teardown_started = asyncio.Event()
    release_second_teardown = asyncio.Event()

    async def provide_first() -> AsyncGenerator[str, None]:
        yield "first"
        events.append("first torn down")

    async def provide_second() -> AsyncGenerator[str, None]:
        yield "second"
        events.append("second teardown started")
        second_teardown_started.set()
        await release_second_teardown.wait()
        events.append("second torn down")

    @get("/", dependencies={"first": Provide(provide_first), "second": Provide(provide_second)})
    async def handler(first: NamedDependency[str], second: NamedDependency[str]) -> str:
        return first + second

    async with AsyncTestClient(Litestar([handler], openapi_config=None)) as client:
        request = asyncio.create_task(client.get("/"))
        await second_teardown_started.wait()
        assert events == ["second teardown started"]
        release_second_teardown.set()
        assert (await request).status_code == 200

    assert events == ["second teardown started", "second torn down", "first torn down"]


def test_dto_decodes_body_declared_only_by_dependency() -> None:
    @dataclass
    class User:
        name: str
        secret: str = "default"

    class UserDTO(DataclassDTO[User]):
        config = DTOConfig(exclude={"secret"})

    async def provide_user(data: Annotated[User, Body()]) -> User:
        return data

    @post("/", dependencies={"user": Provide(provide_user)}, return_dto=None)
    async def handler(user: NamedDependency[User]) -> dict:
        return {"name": user.name, "secret": user.secret}

    with TestClient(Litestar([handler], dto=UserDTO, openapi_config=None)) as client:
        response = client.post("/", json={"name": "x", "secret": "s"})

    assert response.status_code == 201
    assert response.json() == {"name": "x", "secret": "default"}


def test_plugin_dto_decodes_body_declared_only_by_dependency() -> None:
    @dataclass
    class User:
        name: str
        secret: str = "default"

    class UserDTO(DataclassDTO[User]):
        config = DTOConfig(exclude={"secret"})

    class UserSerializationPlugin(SerializationPlugin):
        def supports_type(self, field_definition: FieldDefinition) -> bool:
            return field_definition.is_subclass_of(User)

        def create_dto_for_type(self, field_definition: FieldDefinition) -> type[AbstractDTO]:
            return UserDTO

    async def provide_user(data: Annotated[User, Body()]) -> User:
        return data

    @post("/", dependencies={"user": Provide(provide_user)}, return_dto=None)
    async def handler(user: NamedDependency[User]) -> dict:
        return {"name": user.name, "secret": user.secret}

    with TestClient(Litestar([handler], plugins=[UserSerializationPlugin()], openapi_config=None)) as client:
        response = client.post("/", json={"name": "x", "secret": "s"})

    assert response.status_code == 201
    assert response.json() == {"name": "x", "secret": "default"}


def test_dto_decodes_body_declared_under_other_name_than_data() -> None:
    @dataclass
    class Person:
        name: str
        secret: str = "default"

    class PersonDTO(DataclassDTO[Person]):
        config = DTOConfig(exclude={"secret"})

    @post("/", dto=PersonDTO, return_dto=None)
    async def handler(payload: JSONBody[Person]) -> Person:
        return payload

    with create_test_client([handler]) as client:
        response = client.post("/", json={"name": "a", "secret": "sent"})
        schema = client.app.openapi_schema.to_schema()

    assert response.json() == {"name": "a", "secret": "default"}
    request_body = schema["paths"]["/"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert schema["components"]["schemas"][request_body["$ref"].rsplit("/", 1)[1]]["properties"].keys() == {"name"}


def test_dto_data_declared_under_other_name_than_data() -> None:
    @dataclass
    class Person:
        name: str

    @post("/", dto=DataclassDTO[Person], return_dto=None)
    async def handler(payload: JSONBody[DTOData[Person]]) -> Person:
        return payload.create_instance()

    with create_test_client([handler]) as client:
        assert client.post("/", json={"name": "a"}).json() == {"name": "a"}


def test_dto_data_declared_under_other_name_than_data_without_dto_raises() -> None:
    @dataclass
    class Person:
        name: str

    @post("/")
    async def handler(payload: JSONBody[DTOData[Person]]) -> None: ...

    with pytest.raises(ImproperlyConfiguredException, match="a subclass of DTOData but no DTO has been registered"):
        Litestar([handler], openapi_config=None)


def test_dto_data_declared_only_by_dependency() -> None:
    @dataclass
    class Person:
        name: str

    async def provide_name(data: JSONBody[DTOData[Person]]) -> str:
        return data.create_instance().name

    @post("/", dto=DataclassDTO[Person], return_dto=None, dependencies={"name": Provide(provide_name)})
    async def handler(name: NamedDependency[str]) -> str:
        return name

    with create_test_client([handler]) as client:
        response = client.post("/", json={"name": "a"})

    assert response.status_code == 201
    assert response.text == "a"


def test_dto_data_declared_only_by_dependency_without_dto_raises() -> None:
    @dataclass
    class Person:
        name: str

    async def provide_name(data: JSONBody[DTOData[Person]]) -> str:
        return data.create_instance().name

    @post("/", dependencies={"name": Provide(provide_name)})
    async def handler(name: NamedDependency[str]) -> str:
        return name

    with pytest.raises(ImproperlyConfiguredException, match="a subclass of DTOData but no DTO has been registered"):
        Litestar([handler], openapi_config=None)


def test_dto_not_supporting_body_declared_only_by_dependency_raises() -> None:
    @dataclass
    class Person:
        name: str

    @dataclass
    class Other:
        value: int

    async def provide_value(data: JSONBody[Other]) -> int:
        return data.value

    @post("/", dto=DataclassDTO[Person], return_dto=None, dependencies={"value": Provide(provide_value)})
    async def handler(value: NamedDependency[int]) -> int:
        return value

    with pytest.raises(DTONotApplicableError, match="cannot decode its request body"):
        Litestar([handler], openapi_config=None)


def test_dto_data_declared_by_handler_and_dependency() -> None:
    @dataclass
    class Person:
        name: str

    async def provide_name(data: JSONBody[DTOData[Person]]) -> str:
        return data.create_instance().name

    @post("/", dto=DataclassDTO[Person], return_dto=None, dependencies={"name": Provide(provide_name)})
    async def handler(data: JSONBody[DTOData[Person]], name: NamedDependency[str]) -> list[str]:
        return [data.create_instance().name, name]

    with create_test_client([handler]) as client:
        response = client.post("/", json={"name": "a"})

    assert response.status_code == 201
    assert response.json() == ["a", "a"]


def test_upload_declared_under_other_name_than_data_documented_like_data() -> None:
    @post("/data")
    async def data_handler(data: MultipartBody[UploadFile]) -> None: ...

    @post("/payload")
    async def payload_handler(payload: MultipartBody[UploadFile]) -> None: ...

    paths = Litestar([data_handler, payload_handler]).openapi_schema.to_schema()["paths"]

    assert paths["/payload"]["post"]["requestBody"] == paths["/data"]["post"]["requestBody"]
