# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, make_dataclass
from datetime import date
from decimal import Decimal
from types import ModuleType
from typing import TYPE_CHECKING, Annotated, Generic, Literal, Optional, TypeVar, Union, cast
from unittest.mock import MagicMock

import annotated_types
import msgspec
import pytest
from msgspec import UNSET, Meta, Struct, UnsetType
from typing_extensions import TypeAliasType as TeTypeAliasType

from litestar import Controller, Litestar, Response, get, patch, post
from litestar.connection.request import Request
from litestar.datastructures import UploadFile
from litestar.dto import DataclassDTO, DTOConfig, DTOData, MsgspecDTO, dto_field
from litestar.dto.types import RenameStrategy
from litestar.enums import MediaType
from litestar.exceptions import InvalidAnnotationException
from litestar.params import JSONBody, MultipartBody, QueryParameter, URLEncodedBody
from litestar.serialization import encode_json
from litestar.testing import create_test_client
from tests.helpers import not_none

try:
    from typing import TypeAliasType  # type: ignore[attr-defined]
except ImportError:
    TypeAliasType = TeTypeAliasType

if TYPE_CHECKING:
    from typing import Any


def test_url_encoded_form_data() -> None:
    @dataclass()
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    class UserDTO(DataclassDTO[User]):
        pass

    @post(dto=UserDTO, signature_types=[User])
    def handler(data: URLEncodedBody[User]) -> User:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


async def test_multipart_encoded_form_data() -> None:
    default_file = UploadFile(content_type="text/plain", filename="forbidden", file_data=b"forbidden")

    @dataclass
    class Payload:
        file: UploadFile
        forbidden: UploadFile = field(
            default=default_file,
            metadata=dto_field("read-only"),
        )

    class PayloadDTO(DataclassDTO[Payload]):
        pass

    @post(dto=PayloadDTO, return_dto=None, signature_types=[Payload], media_type=MediaType.TEXT)
    async def handler(data: MultipartBody[Payload]) -> bytes:
        return await data.forbidden.read()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            files={"file": b"abc123", "forbidden": b"123abc"},
        )
        assert response.content == b"forbidden"

    await default_file.close()


def test_renamed_field() -> None:
    @dataclass
    class Foo:
        bar: str

    config = DTOConfig(rename_fields={"bar": "baz"})
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_types=[Foo])
    def handler(data: JSONBody[Foo]) -> Foo:
        assert data.bar == "hello"
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"baz": "hello"})
        assert response.json() == {"baz": "hello"}


def test_renamed_field_nested(create_module: Callable[[str], ModuleType]) -> None:
    # https://github.com/litestar-org/litestar/issues/2721
    module = create_module(
        """
from dataclasses import dataclass
from typing import List

@dataclass
class Bar:
    id: str

@dataclass
class Foo:
    id: str
    bar: Bar
    bars: list[Bar]
"""
    )

    Foo = module.Foo

    config = DTOConfig(
        rename_fields={"id": "foo_id", "bar.id": "bar_id", "bars.0.id": "bars_id"},
    )
    dto = DataclassDTO[Annotated[Foo, config]]  # type: ignore[valid-type]

    @post(dto=dto, signature_types=[Foo])
    def handler(data: JSONBody[Foo]) -> Foo:  # type: ignore[valid-type]
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"foo_id": "1", "bar": {"bar_id": "2"}, "bars": [{"bars_id": "3"}]})
        assert response.json() == {"foo_id": "1", "bar": {"bar_id": "2"}, "bars": [{"bars_id": "3"}]}


@dataclass
class Spam:
    main_id: str = "spam-id"


@dataclass
class Fzop:
    bar: str = "hello"
    SPAM: str = "bye"
    spam_bar: str = "welcome"
    spam_model: Optional[Spam] = None


@pytest.mark.parametrize(
    "rename_strategy, instance, tested_fields, data",
    [
        ("upper", Fzop(bar="hi"), ["BAR"], {"BAR": "hi"}),
        ("lower", Fzop(SPAM="goodbye"), ["spam"], {"spam": "goodbye"}),
        (lambda x: x[::-1], Fzop(bar="h", SPAM="bye!"), ["rab", "MAPS"], {"rab": "h", "MAPS": "bye!"}),
        ("camel", Fzop(spam_bar="star"), ["spamBar"], {"spamBar": "star"}),
        ("pascal", Fzop(spam_bar="star"), ["SpamBar"], {"SpamBar": "star"}),
        ("camel", Fzop(spam_model=Spam()), ["spamModel"], {"spamModel": {"mainId": "spam-id"}}),
        (
            "kebab",
            Fzop(spam_bar="star", spam_model=Spam()),
            ["spam-bar", "spam-model"],
            {"spam-bar": "star", "spam-model": {"main-id": "spam-id"}},
        ),
    ],
)
def test_fields_alias_generator(
    rename_strategy: RenameStrategy,
    instance: Fzop,
    tested_fields: list[str],
    data: dict[str, str],
) -> None:
    config = DTOConfig(rename_strategy=rename_strategy)
    dto = DataclassDTO[Annotated[Fzop, config]]

    @post(dto=dto)
    def handler(data: JSONBody[Fzop]) -> Fzop:
        assert data.bar == instance.bar
        assert data.SPAM == instance.SPAM
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json=data)
        for f in tested_fields:
            assert response.json()[f] == data[f]


def test_dto_data_injection() -> None:
    @dataclass
    class Foo:
        bar: str

    @post(dto=DataclassDTO[Foo], return_dto=None, signature_types=[Foo])
    def handler(data: JSONBody[DTOData[Foo]]) -> Foo:
        assert isinstance(data, DTOData)
        assert data.as_builtins() == {"bar": "hello"}
        assert isinstance(data.create_instance(), Foo)
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello"})
        assert response.json() == {"bar": "hello"}


@dataclass
class NestedFoo:
    bar: str
    baz: str


@dataclass
class NestingBar:
    foo: NestedFoo


def test_dto_data_injection_with_nested_model() -> None:
    @post(
        dto=DataclassDTO[Annotated[NestingBar, DTOConfig(exclude={"foo.baz"})]],
        return_dto=None,
    )
    def handler(data: JSONBody[DTOData[NestingBar]]) -> dict[str, Any]:
        assert isinstance(data, DTOData)
        return cast("dict[str, Any]", data.as_builtins())

    with create_test_client(route_handlers=[handler]) as client:
        resp = client.post("/", json={"foo": {"bar": "hello"}})
        assert resp.status_code == 201
        assert resp.json() == {"foo": {"bar": "hello"}}


def test_dto_data_create_instance_nested_kwargs() -> None:
    @post(
        dto=DataclassDTO[Annotated[NestingBar, DTOConfig(exclude={"foo.baz"})]],
        return_dto=None,
    )
    def handler(data: JSONBody[DTOData[NestingBar]]) -> NestingBar:
        assert isinstance(data, DTOData)
        result = data.create_instance(foo__baz="world")
        assert result.foo.baz == "world"
        return result

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"foo": {"bar": "hello"}})
        assert response.status_code == 201
        assert response.json() == {"foo": {"bar": "hello", "baz": "world"}}


@dataclass
class Dog:
    id: int
    nick_name: str
    secret: str = field(default="s", metadata=dto_field("private"))


@dataclass
class Cat:
    id: int
    color: str


@dataclass
class Person:
    id: int
    name: str
    pets: tuple[Dog, Cat]


def test_dto_fixed_length_tuple_excludes_and_renames_nested_fields() -> None:
    received: dict[str, Person] = {}

    @get(
        "/",
        return_dto=DataclassDTO[
            Annotated[Person, DTOConfig(exclude={"id", "pets.0.id", "pets.1.id"}, rename_strategy="camel")]
        ],
    )
    def read_person() -> Person:
        return Person(id=1, name="John", pets=(Dog(id=2, nick_name="Dog"), Cat(id=3, color="White")))

    @post(
        "/",
        dto=DataclassDTO[Annotated[Person, DTOConfig(rename_fields={"pets.0.nick_name": "nn"})]],
        return_dto=None,
    )
    def write_person(data: JSONBody[Person]) -> None:
        received["data"] = data

    with create_test_client(route_handlers=[read_person, write_person]) as client:
        assert client.get("/").json() == {"name": "John", "pets": [{"nickName": "Dog"}, {"color": "White"}]}
        response = client.post(
            "/", json={"id": 1, "name": "n", "pets": [{"id": 7, "nn": "d"}, {"id": 8, "color": "c"}]}
        )
        assert response.status_code == 201
        assert received["data"].pets == (Dog(id=7, nick_name="d"), Cat(id=8, color="c"))


@dataclass
class TupleMember:
    y: int


@dataclass
class TupleHolder:
    t: tuple[TupleMember, int] = (TupleMember(y=1), 2)
    u: Optional[tuple[TupleMember, int]] = None
    lt: list[tuple[TupleMember, str]] = field(default_factory=list)


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            TupleHolder(u=(TupleMember(y=3), 4), lt=[(TupleMember(y=9), "a")]),
            {"t": [{}, 2], "u": [{}, 4], "lt": [[{}, "a"]]},
        ),
        (TupleHolder(), {"t": [{}, 2], "u": None, "lt": []}),
    ],
)
def test_dto_fixed_length_tuple_inside_union_and_list(value: TupleHolder, expected: dict[str, Any]) -> None:
    @get("/", return_dto=DataclassDTO[Annotated[TupleHolder, DTOConfig(exclude={"t.0.y", "u.0.0.y", "lt.0.0.y"})]])
    def read_tuple_holder() -> TupleHolder:
        return value

    with create_test_client(route_handlers=[read_tuple_holder]) as client:
        assert client.get("/").json() == expected


@pytest.mark.parametrize("value", [(TupleMember(1),), (TupleMember(1), 2, 3)])
def test_dto_fixed_length_tuple_of_wrong_length_fails(value: tuple[Any, ...]) -> None:
    @get("/", return_dto=DataclassDTO[TupleHolder])
    def read_wrong_length() -> TupleHolder:
        return TupleHolder(t=value)

    with create_test_client(route_handlers=[read_wrong_length], raise_server_exceptions=False) as client:
        assert client.get("/").status_code == 500


@dataclass
class User:
    name: str
    age: int
    read_only: str = field(default="read-only", metadata=dto_field("read-only"))


def test_dto_data_with_url_encoded_form_data() -> None:
    @post(dto=DataclassDTO[User])
    def handler(data: URLEncodedBody[DTOData[User]]) -> User:
        return data.create_instance()

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"id=1&name=John&age=42&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John", "age": 42, "read_only": "read-only"}


RenamedBarT = TypeVar("RenamedBarT")


@dataclass
class GenericRenamedBar(Generic[RenamedBarT]):
    bar: str
    spam_bar: RenamedBarT
    foo_foo: str


@dataclass
class InnerBar:
    best_greeting: str


@dataclass
class RenamedBar(GenericRenamedBar[InnerBar]):
    pass


def test_dto_data_create_instance_renamed_fields() -> None:
    @post(
        dto=DataclassDTO[
            Annotated[
                RenamedBar,
                DTOConfig(
                    exclude={"foo_foo"},
                    rename_strategy="camel",
                ),
            ]
        ],
        return_dto=DataclassDTO[
            Annotated[
                RenamedBar,
                DTOConfig(rename_strategy="camel"),
            ]
        ],
    )
    def handler(data: JSONBody[DTOData[RenamedBar]]) -> RenamedBar:
        assert isinstance(data, DTOData)
        result = data.create_instance(foo_foo="world")
        assert result.foo_foo == "world"
        assert result.spam_bar.best_greeting == "hello world"
        return result

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "spamBar": {"bestGreeting": "hello world"}})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello", "fooFoo": "world", "spamBar": {"bestGreeting": "hello world"}}


def test_dto_data_with_patch_request() -> None:
    class PatchDTO(DataclassDTO[User]):
        config = DTOConfig(partial=True)

    @patch(dto=PatchDTO, return_dto=None)
    def handler(data: JSONBody[DTOData[User]]) -> User:
        return data.update_instance(User(name="John", age=42))

    with create_test_client(route_handlers=[handler]) as client:
        response = client.patch("/", json={"age": 41, "read_only": "whoops"})
        assert response.json() == {"name": "John", "age": 41, "read_only": "read-only"}


@dataclass
class UniqueModelName:
    id: int
    foo: str


def test_dto_openapi_with_unique_handler_names() -> None:
    @post(
        dto=DataclassDTO[Annotated[UniqueModelName, DTOConfig(exclude={"id"})]],
        return_dto=DataclassDTO[UniqueModelName],
        signature_namespace={"UniqueModelName": UniqueModelName},
    )
    def handler(data: JSONBody[UniqueModelName]) -> UniqueModelName:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 2
        assert schemas[0]["title"] == "UniqueModelNameRequestBody_fb568797"
        assert schemas[1]["title"] == "UniqueModelNameResponseBody"


@dataclass
class SharedModelName:
    id: int
    foo: str


def test_dto_openapi_without_unique_handler_names() -> None:
    write_dto = DataclassDTO[Annotated[SharedModelName, DTOConfig(exclude={"id"})]]
    read_dto = DataclassDTO[SharedModelName]

    @post(dto=write_dto, return_dto=read_dto)
    def handler(data: JSONBody[SharedModelName]) -> SharedModelName:
        return data

    class MyController(Controller):
        path = "/sub-path"

        @post(dto=write_dto, return_dto=read_dto)
        def handler(self, data: JSONBody[SharedModelName]) -> SharedModelName:
            return data

    with create_test_client(route_handlers=[handler, MyController]) as client:
        response = client.get("/schema/openapi.json")
        schemas = list(response.json()["components"]["schemas"].values())
        assert len(schemas) == 2
        assert schemas[0]["title"] == "SharedModelNameRequestBody_fb568797"
        assert schemas[1]["title"] == "SharedModelNameResponseBody"


def test_url_encoded_form_data_patch_request() -> None:
    @dataclass()
    class User:
        name: str
        age: int
        read_only: str = field(default="read-only", metadata=dto_field("read-only"))

    dto = DataclassDTO[Annotated[User, DTOConfig(partial=True)]]

    @post(dto=dto, return_dto=None, signature_types=[User])
    def handler(data: URLEncodedBody[DTOData[User]]) -> dict[str, Any]:
        return data.as_builtins()  # type:ignore[no-any-return]

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post(
            "/",
            content=b"name=John&read_only=whoops",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.json() == {"name": "John"}


def test_dto_with_generic_sequence_annotations() -> None:
    @dataclass
    class User:
        name: str
        age: int

    @post(
        dto=DataclassDTO[User],
        signature_types=[User],
    )
    def handler(data: JSONBody[Sequence[User]]) -> Sequence[User]:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json=[{"name": "John", "age": 42}])
        assert response.json() == [{"name": "John", "age": 42}]


def test_dto_private_fields() -> None:
    @dataclass
    class Foo:
        bar: str
        _baz: int

    mock = MagicMock()

    @post(
        dto=DataclassDTO[Foo],
        signature_types=[Foo],
    )
    def handler(data: JSONBody[DTOData[Foo]]) -> Foo:
        mock.received_data = data.as_builtins()
        return data.create_instance(_baz=42)

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "_baz": "world"})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello"}

    assert mock.received_data == {"bar": "hello"}


def test_dto_private_fields_disabled() -> None:
    @dataclass
    class Foo:
        bar: str
        _baz: int

    @post(
        dto=DataclassDTO[
            Annotated[
                Foo,
                DTOConfig(underscore_fields_private=False),
            ]
        ],
        signature_types=[Foo],
    )
    def handler(data: JSONBody[Foo]) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "_baz": 42})
        assert response.status_code == 201
        assert response.json() == {"bar": "hello", "_baz": 42}


def test_dto_concrete_builtin_collection_types() -> None:
    @dataclass
    class Foo:
        bar: dict
        baz: list

    @post(
        dto=DataclassDTO[
            Annotated[
                Foo,
                DTOConfig(underscore_fields_private=False),
            ]
        ],
        signature_types=[Foo],
    )
    def handler(data: JSONBody[Foo]) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]})
        assert response.status_code == 201
        assert response.json() == {"bar": {"a": 1, "b": [1, 2, 3]}, "baz": [4, 5, 6]}


@dataclass
class WrappedUser:
    name: str
    age: int


T = TypeVar("T")
V = TypeVar("V")
K = TypeVar("K")


@dataclass
class Wrapped(Generic[T, V]):
    data: T
    other: V


def test_dto_generic_dataclass_wrapped_list_response() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Wrapped[list[WrappedUser], int]:
        return Wrapped(
            data=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)],
            other=2,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"data": [{"name": "John"}, {"name": "Jane"}], "other": 2}


@dataclass
class WrappedWithCollection(Generic[T, V]):
    items: list[T]
    other: V


def test_dto_generic_dataclass_wrapped_collection_response() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> WrappedWithCollection[WrappedUser, int]:
        return WrappedWithCollection(
            items=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)],
            other=2,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"items": [{"name": "John"}, {"name": "Jane"}], "other": 2}


def test_dto_generic_dataclass_wrapped_scalar_response() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Wrapped[WrappedUser, int]:
        return Wrapped(
            data=WrappedUser(name="John", age=42),
            other=2,
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"data": {"name": "John"}, "other": 2}


@dataclass
class WrappedWithDict(Generic[K, V, T]):
    data: T
    other: dict[K, V]


def test_dto_generic_dataclass_wrapped_scalar_response_with_additional_mapping_data() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> WrappedWithDict[str, int, WrappedUser]:
        return WrappedWithDict(
            data=WrappedUser(name="John", age=42),
            other={"a": 1, "b": 2},
        )

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"data": {"name": "John"}, "other": {"a": 1, "b": 2}}


def test_dto_response_wrapped_scalar_return_type() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Response[WrappedUser]:
        return Response(content=WrappedUser(name="John", age=42))

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == {"name": "John"}

        schema_response = client.get("/schema/openapi.json")
        schemas = list(schema_response.json()["components"]["schemas"].values())
        assert len(schemas) == 1
        assert schemas[0]["title"] == "WrappedUserResponseBody_af598c51"


def test_dto_response_wrapped_collection_return_type() -> None:
    @get(dto=DataclassDTO[Annotated[WrappedUser, DTOConfig(exclude={"age"})]])
    def handler() -> Response[list[WrappedUser]]:
        return Response(content=[WrappedUser(name="John", age=42), WrappedUser(name="Jane", age=43)])

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.json() == [{"name": "John"}, {"name": "Jane"}]

        schema_response = client.get("/schema/openapi.json")
        schemas = list(schema_response.json()["components"]["schemas"].values())
        assert len(schemas) == 1
        assert schemas[0]["title"] == "WrappedUserResponseBody_af598c51"


def test_schema_required_fields_with_msgspec_dto() -> None:
    class MsgspecUser(Struct):
        age: int
        name: str

    class UserDTO(MsgspecDTO[MsgspecUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[MsgspecUser])
    def handler(data: JSONBody[MsgspecUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = MsgspecUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2


def test_schema_required_fields_with_dataclass_dto() -> None:
    @dataclass
    class DataclassUser:
        age: int
        name: str

    class UserDTO(DataclassDTO[DataclassUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[DataclassUser])
    def handler(data: JSONBody[DataclassUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = DataclassUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert len(required) == 2


def test_schema_required_fields_with_msgspec_dto_and_default_fields() -> None:
    class MsgspecUser(Struct):
        age: int
        name: str = "A"

    class UserDTO(MsgspecDTO[MsgspecUser]):
        pass

    @post(dto=UserDTO, return_dto=None, signature_types=[MsgspecUser])
    def handler(data: JSONBody[MsgspecUser], request: Request) -> dict:
        schema = request.app.openapi_schema
        return schema.to_schema()

    with create_test_client(handler) as client:
        data = MsgspecUser(name="A", age=10)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        received = client.post(
            "/",
            content=msgspec.json.encode(data),
            headers=headers,
        )
        required = next(iter(received.json()["components"]["schemas"].values()))["required"]
        assert required == ["age"]


X = TypeVar("X", bound=Struct)


class ClassicNameStyle(Struct):
    first_name: str
    surname: str


class BoundUser(Struct, Generic[X]):
    age: int
    data: X


class Superuser(BoundUser[ClassicNameStyle]):
    pass


def test_dto_with_msgspec_with_bound_generic_and_inherited_models() -> None:
    @post(dto=MsgspecDTO[Superuser])
    def handler(data: JSONBody[Superuser]) -> Superuser:
        return data

    with create_test_client(handler) as client:
        data = Superuser(data=ClassicNameStyle(first_name="A", surname="B"), age=10)
        received = client.post(
            "/",
            content=encode_json(data),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        assert msgspec.json.decode(received.content, type=Superuser) == data


def test_dto_returning_mapping() -> None:
    @dataclass
    class Lexeme:
        id: int
        name: str

    class LexemeDTO(DataclassDTO[Lexeme]):
        config = DTOConfig(exclude={"id"})

    @get(return_dto=LexemeDTO, signature_types=[Lexeme])
    async def get_definition() -> dict[str, Lexeme]:
        return {"hello": Lexeme(id=1, name="hello"), "world": Lexeme(id=2, name="world")}

    with create_test_client(route_handlers=[get_definition]) as client:
        response = client.get("/")
        assert response.json() == {"hello": {"name": "hello"}, "world": {"name": "world"}}


def test_data_dto_with_default() -> None:
    """A POST request without Body should inject the default value.

    https://github.com/litestar-org/litestar/issues/2902
    """

    @dataclass
    class Foo:
        foo: str

    @post(path="/", dto=DataclassDTO[Foo], signature_types=[Foo])
    def test(data: JSONBody[Optional[Foo]] = None) -> dict:
        return {"foo": data}

    with create_test_client([test]) as client:
        response = client.post("/")
        assert response.json() == {"foo": None}


@pytest.mark.parametrize(
    "field_type, constraint_name, constraint_value, request_data",
    [
        (int, "gt", 2, 2),
        (int, "ge", 2, 1),
        (int, "lt", 2, 2),
        (int, "le", 2, 3),
        (int, "multiple_of", 2, 3),
        (str, "min_length", 2, "1"),
        (str, "max_length", 1, "12"),
        (str, "pattern", r"\d", "a"),
    ],
)
def test_msgspec_dto_copies_constraints(
    field_type: Any, constraint_name: str, constraint_value: Any, request_data: Any
) -> None:
    # https://github.com/litestar-org/litestar/issues/3026
    struct = msgspec.defstruct(
        "Foo",
        fields=[("bar", Annotated[field_type, msgspec.Meta(**{constraint_name: constraint_value})])],  # type: ignore[list-item]
    )

    @post(
        "/",
        dto=MsgspecDTO[struct],  # type: ignore[valid-type]
        signature_namespace={"struct": struct},
    )
    def handler(data: JSONBody[struct]) -> None:  # type: ignore[valid-type]
        pass

    with create_test_client([handler]) as client:
        assert client.post("/", json={"bar": request_data}).status_code == 400


def test_msgspec_dto_copies_length_constraints_for_partial_dto() -> None:
    class Foo(msgspec.Struct):
        bar: Annotated[str, msgspec.Meta(min_length=2)]
        baz: Annotated[str, msgspec.Meta(max_length=2)]

    class FooDTO(MsgspecDTO[Foo]):
        config = DTOConfig(partial=True)

    @post("/", dto=FooDTO, return_dto=None, signature_types={Foo})
    def handler(data: JSONBody[DTOData[Foo]]) -> None:
        pass

    with create_test_client([handler]) as client:
        assert client.post("/", json={"bar": "1"}).status_code == 400
        assert client.post("/", json={"baz": "123"}).status_code == 400
        assert client.post("/", json={"bar": "12", "baz": "12"}).status_code == 201
        assert client.post("/", json={}).status_code == 201


def _make_model(dto_type: Any, annotation: Any, **default: Any) -> Any:
    if dto_type is DataclassDTO:
        return make_dataclass("Model", [("f", annotation, field(**default))])
    return msgspec.defstruct("Model", [("f", annotation, msgspec.field(**default))])


def _create_client(dto_type: Any, model: Any, partial: bool = False) -> Any:
    async def create(data: Any) -> None:
        return None

    json_body: Any = JSONBody
    dto_data: Any = DTOData
    create.__annotations__["data"] = json_body[dto_data[model] if partial else model]
    dto = dto_type[Annotated[model, DTOConfig(partial=True)]] if partial else dto_type[model]
    return create_test_client([post("/", dto=dto, return_dto=None)(create)], openapi_config=None)


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize(
    "annotation, default, invalid, valid",
    [
        pytest.param(
            Union[Annotated[str, Meta(min_length=8)], UnsetType], {"default": UNSET}, "12", "12345678", id="issue_4181"
        ),
        pytest.param(Optional[Annotated[str, Meta(pattern="^a")]], {"default": None}, "b", "ab", id="issue_4195"),
        pytest.param(Optional[Annotated[str, Meta(min_length=2)]], {"default": None}, "1", "12", id="issue_5025"),
        pytest.param(Union[Annotated[str, Meta(min_length=5)], int], {"default": 0}, "12", 3, id="issue_5031"),
        pytest.param(
            list[Annotated[str, Meta(min_length=5)]], {"default_factory": list}, ["12"], ["12345"], id="issue_5051"
        ),
    ],
)
def test_msgspec_dto_enforces_member_constraints_of_reported_issues(
    partial: bool, annotation: Any, default: dict[str, Any], invalid: Any, valid: Any
) -> None:
    with _create_client(MsgspecDTO, _make_model(MsgspecDTO, annotation, **default), partial) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201
        assert client.post("/", json={}).status_code == 201


_MEMBER_CONSTRAINT_CASES = [
    pytest.param(list[Annotated[str, Meta(min_length=5)]], ["12"], ["12345"], id="list_item"),
    pytest.param(dict[str, Annotated[str, Meta(min_length=5)]], {"k": "12"}, {"k": "12345"}, id="dict_value"),
    pytest.param(dict[Annotated[str, Meta(min_length=5)], int], {"k": 1}, {"kkkkk": 1}, id="dict_key"),
    pytest.param(tuple[Annotated[str, Meta(min_length=5)], int], ["12", 1], ["12345", 1], id="tuple_member"),
    pytest.param(Union[Annotated[str, Meta(min_length=5)], int], "12", 3, id="union_member"),
]


@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize("annotation, invalid, valid", _MEMBER_CONSTRAINT_CASES)
def test_dto_enforces_member_constraints(dto_type: Any, annotation: Any, invalid: Any, valid: Any) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation)) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201


Limit = TypeAliasType("Limit", Annotated[int, Meta(ge=0)])


@pytest.mark.parametrize("partial", [False, True])
@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
@pytest.mark.parametrize(
    "annotation, default, invalid, valid",
    [
        pytest.param(Annotated[int, Meta(ge=1)], {"default": 1}, 0, 2, id="meta_ge"),
        pytest.param(
            Annotated[list[int], Meta(min_length=2)], {"default_factory": list}, [1], [1, 2], id="meta_list_length"
        ),
        pytest.param(
            Limit,
            {"default": 0},
            -1,
            1,
            id="type_alias",
            marks=pytest.mark.skipif(sys.version_info < (3, 12), reason="msgspec decodes typing.TypeAliasType only"),
        ),
        pytest.param(
            Annotated[str, annotated_types.MinLen(5)], {"default": "12345"}, "12", "123456", id="annotated_types"
        ),
        pytest.param(
            Annotated[str, QueryParameter(max_length=2)], {"default": "1"}, "123", "12", id="parameter_definition"
        ),
    ],
)
def test_dto_enforces_field_constraints(
    dto_type: Any, partial: bool, annotation: Any, default: dict[str, Any], invalid: Any, valid: Any
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation, **default), partial) as client:
        assert client.post("/", json={"f": invalid}).status_code == 400
        assert client.post("/", json={"f": valid}).status_code == 201


@pytest.mark.parametrize(
    "dto_type, annotation, invalid, valid",
    [
        pytest.param(MsgspecDTO, Annotated[Decimal, annotated_types.Gt(0)], "0", "1", id="decimal_gt"),
        pytest.param(DataclassDTO, list[Annotated[Decimal, annotated_types.Gt(0)]], ["0"], ["1"], id="decimal_item"),
        pytest.param(MsgspecDTO, Annotated[int, annotated_types.Ge(1.5)], 1, 2, id="int_float_bound"),
        pytest.param(
            DataclassDTO, Annotated[date, annotated_types.Ge(date(2020, 1, 1))], "2019-01-01", "2021-01-01", id="date"
        ),
        pytest.param(DataclassDTO, Annotated[Optional[int], annotated_types.Ge(0)], -1, 1, id="optional_ge"),
        pytest.param(MsgspecDTO, Annotated[Union[str, int], annotated_types.MinLen(2)], "a", "ab", id="union_min_len"),
        pytest.param(DataclassDTO, Annotated[int, annotated_types.Ge(1), annotated_types.Gt(0)], 0, 3, id="conflict"),
    ],
)
def test_dto_does_not_enforce_derived_constraints_msgspec_cannot_express(
    dto_type: Any, annotation: Any, invalid: Any, valid: Any
) -> None:
    with _create_client(dto_type, _make_model(dto_type, annotation)) as client:
        assert client.post("/", json={"f": invalid}).status_code == 201
        assert client.post("/", json={"f": valid}).status_code == 201


@pytest.mark.parametrize("dto_type", [DataclassDTO, MsgspecDTO])
def test_dto_raises_at_startup_for_an_invalid_pattern(dto_type: Any) -> None:
    with pytest.raises(re.error):
        _create_client(dto_type, _make_model(dto_type, Annotated[str, QueryParameter(pattern="(")]))


@dataclass
class ReturnedModel:
    violating: Annotated[str, Meta(min_length=5)] = "12"
    misplaced: Annotated[Optional[str], Meta(min_length=5, description="d")] = "12"
    member: list[Annotated[int, Meta(min_length=1)]] = field(default_factory=lambda: [1])


def test_return_dto_does_not_apply_constraints_and_keeps_their_schema_attributes() -> None:
    @get("/", return_dto=DataclassDTO[ReturnedModel])
    def read_returned() -> ReturnedModel:
        return ReturnedModel()

    with create_test_client([read_returned]) as client:
        assert client.get("/").json() == {"violating": "12", "misplaced": "12", "member": [1]}
        (component,) = client.get("/schema/openapi.json").json()["components"]["schemas"].values()

    assert component["properties"]["misplaced"]["description"] == "d"


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param(Annotated[Optional[str], Meta(min_length=5)], id="optional_meta"),
        pytest.param(list[Annotated[int, Meta(min_length=1)]], id="item_meta"),
    ],
)
def test_data_dto_raises_at_startup_when_msgspec_rejects_the_transfer_type(annotation: Any) -> None:
    model = _make_model(DataclassDTO, annotation)

    @post("/", dto=DataclassDTO[model], return_dto=None, signature_namespace={"model": model})  # type: ignore[valid-type]
    def create_rejected(data: JSONBody[model]) -> None:  # type: ignore[valid-type]
        pass

    with pytest.raises(InvalidAnnotationException, match="min_length") as exc_info:
        Litestar(route_handlers=[create_rejected], openapi_config=None)

    message = str(exc_info.value)
    assert message.startswith("msgspec cannot decode the transfer model of ")
    assert "field 'f'" in message
    assert repr(annotation) in message
    assert "create_rejected" in message
    assert "attach the constraint to the member type it applies to" in message
    assert isinstance(exc_info.value.__cause__, TypeError)


@dataclass
class RejectedInner:
    g: Annotated[Optional[str], Meta(min_length=5)] = None


@dataclass
class RejectedOuter:
    _hidden: int
    inners: dict[str, RejectedInner]


@dataclass
class U1:
    a: int


@dataclass
class U2:
    b: int


@dataclass
class UH:
    f: Union[U1, U2]


@pytest.mark.parametrize(
    "model, expected",
    [
        pytest.param(RejectedOuter, f"field 'g' of '{__name__}.RejectedInner'", id="nested_field"),
        pytest.param(UH, f"field 'f' of '{__name__}.UH'", id="union_of_models"),
    ],
)
def test_data_dto_startup_error_names_the_innermost_field(model: Any, expected: str) -> None:
    @post("/", dto=DataclassDTO[model], return_dto=None, signature_namespace={"model": model})
    def create_rejected_outer(data: JSONBody[model]) -> None:  # pyright: ignore[reportInvalidTypeForm]
        pass

    with pytest.raises(InvalidAnnotationException) as exc_info:
        Litestar(route_handlers=[create_rejected_outer], openapi_config=None)

    assert expected in str(exc_info.value)
    assert "RequestBody" not in str(exc_info.value)
    if model is UH:
        assert "tag the union members or decode the body yourself" in str(exc_info.value)


class OwnDecode(DataclassDTO[UH]):
    def decode_bytes(self, value: bytes) -> Any:
        raw = msgspec.json.decode(value)
        return UH(f=U1(**raw["f"]) if "a" in raw["f"] else U2(**raw["f"]))


def test_data_dto_with_own_decoding_is_not_checked_at_startup() -> None:
    @post("/", dto=OwnDecode, return_dto=None)
    def create_own_decoded(data: JSONBody[UH]) -> UH:
        return data

    with create_test_client([create_own_decoded], openapi_config=None) as client:
        assert client.post("/", json={"f": {"a": 1}}).json() == {"f": {"a": 1}}


@pytest.mark.parametrize(
    "annotation, match",
    [
        pytest.param(
            Annotated[Optional[str], Meta(min_length=5)],
            r"^msgspec cannot inspect .*field 'f'.*min_length.*attach the constraint to the member type",
            id="optional_meta",
        ),
        pytest.param(Literal[1, "a"], "^msgspec cannot inspect", id="mixed_literal"),
    ],
)
def test_msgspec_dto_raises_invalid_annotation_when_msgspec_rejects_the_model(annotation: Any, match: str) -> None:
    struct = msgspec.defstruct("Model", [("f", annotation, None)])

    @get("/", return_dto=MsgspecDTO[struct], signature_namespace={"struct": struct})  # type: ignore[valid-type]
    def read_rejected_struct() -> struct:  # type: ignore[valid-type]
        return struct()

    with pytest.raises(InvalidAnnotationException, match=match) as exc_info:
        Litestar(route_handlers=[read_rejected_struct], openapi_config=None)

    assert isinstance(exc_info.value.__cause__, TypeError)


def test_openapi_schema_for_type_with_custom_generic_type(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, List, TypeVar

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from litestar import Litestar, get
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO
from litestar.dto import DTOConfig

T = TypeVar("T")

@dataclass
class WithCount(Generic[T]):
    count: int
    data: list[T]

class Base(DeclarativeBase): ...

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    password: Mapped[str]
    created_at: Mapped[datetime]

class UserDTO(SQLAlchemyDTO[User]):
    config = DTOConfig(exclude={"password", "created_at"})

@get("/users", dto=UserDTO, sync_to_thread=False)
def get_users() -> WithCount[User]:
    return WithCount(
        count=1, data=[User(id=1, name="Litestar User", password="xyz", created_at=datetime.now())]
    )

app = Litestar(route_handlers=[get_users])
"""
    )
    openapi = cast("Litestar", module.app).openapi_schema
    schema = openapi.components.schemas["WithCount_UserDTOResponseBody_"]
    assert not_none(schema.properties).keys() == {"count", "data"}
    model_schema = openapi.components.schemas["UserDTOResponseBody"]
    assert not_none(model_schema.properties).keys() == {"id", "name"}


def test_openapi_schema_for_type_with_litestar_response_generic_type(
    create_module: Callable[[str], ModuleType],
) -> None:
    module = create_module("""
from dataclasses import dataclass
from typing import List

from litestar import Litestar, Response, get
from litestar.dto import DataclassDTO, DTOConfig


@dataclass
class Item:
    id: int
    name: str
    secret: str


class ItemReadDTO(DataclassDTO[Item]):
    config = DTOConfig(exclude=["secret"])


@get("/get_items", return_dto=ItemReadDTO)
async def get_items() -> Response[List[Item]]:
    return Response(
        headers={"X-SomeParam": "SomeValue"},
        content=[
            Item(id=1, name="Item 1", secret="123"),
            Item(id=2, name="Item 2", secret="456"),
        ],
    )

app = Litestar(route_handlers=[get_items])
""")

    openapi = cast("Litestar", module.app).openapi_schema
    schema = openapi.components.schemas["ItemReadDTOResponseBody"]
    assert not_none(schema.properties).keys() == {"id", "name"}


def test_openapi_schema_for_dto_includes_body_examples(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from uuid import UUID

from typing_extensions import Annotated

from litestar import Litestar, post
from litestar.dto import DataclassDTO
from litestar.openapi.spec import Example
from litestar.params import Body


@dataclass
class Item:
    id: UUID
    name: str


body = Body(
    title="Create item",
    description="Create a new item.",
    examples=[
        Example(
            summary="Post is Ok",
            value={
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Swatch",
            },
        )
    ],
)


@post()
async def create_item(data: Annotated[Item, body]) -> Item:
    return data


@post("dto", dto=DataclassDTO[Item])
async def create_item_with_dto(data: Annotated[Item, body]) -> Item:
    return data


app = Litestar(route_handlers=[create_item, create_item_with_dto])
"""
    )

    openapi_schema = module.app.openapi_schema
    item_schema = openapi_schema.components.schemas["Item"]
    item_with_dto_schema = openapi_schema.components.schemas["ItemRequestBody"]
    assert item_schema.examples == item_with_dto_schema.examples


@pytest.mark.parametrize("forbid_unknown_fields, expected_status_code", [(False, 201), (True, 400)])
def test_forbid_unknown_fields(forbid_unknown_fields: bool, expected_status_code: int) -> None:
    @dataclass
    class Foo:
        bar: str

    config = DTOConfig(
        forbid_unknown_fields=forbid_unknown_fields,
    )
    dto = DataclassDTO[Annotated[Foo, config]]

    @post(dto=dto, signature_types=[Foo])
    def handler(data: JSONBody[Foo]) -> Foo:
        return data

    with create_test_client(route_handlers=[handler]) as client:
        response = client.post("/", json={"bar": "hello", "baz": "given"})
        assert response.status_code == expected_status_code
