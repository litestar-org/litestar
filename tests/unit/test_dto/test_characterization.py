import dataclasses
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, Generic, Protocol, TypeVar

import msgspec
import pytest

from litestar import Litestar, Response, get, patch, post
from litestar.dto import DataclassDTO, DTOConfig, DTOData, DTOField, Mark
from litestar.params import JSONBody
from litestar.testing import TestClient

T = TypeVar("T")
Fn = TypeVar("Fn", bound=Callable[..., Any])


class Distinct(Protocol):
    def __call__(self, fn: Fn, /) -> Fn: ...


@pytest.fixture(params=[True, False], ids=["codegen", "interp"])
def codegen(request: pytest.FixtureRequest) -> bool:
    return bool(request.param)


@pytest.fixture
def distinct(request: pytest.FixtureRequest) -> Distinct:
    suffix = re.sub(r"\W+", "_", request.node.name)

    def rename(fn: Fn) -> Fn:
        fn.__qualname__ = f"{fn.__qualname__}_{suffix}"
        return fn

    return rename


def client(*handlers: Any) -> TestClient[Litestar]:
    return TestClient(Litestar(handlers, openapi_config=None), raise_server_exceptions=False)


@dataclass
class Account:
    public: str = "d-public"
    listed: str = "d-listed"
    private: Annotated[str, DTOField(mark=Mark.PRIVATE)] = "d-private"
    read_only: Annotated[str, DTOField(mark=Mark.READ_ONLY)] = "d-read-only"
    write_only: Annotated[str, DTOField(mark=Mark.WRITE_ONLY)] = "d-write-only"
    _under: str = "d-under"


ALL_FIELDS = {"public", "listed", "private", "read_only", "write_only", "_under"}
EXCLUSION_MATRIX: list[tuple[str, dict[str, Any], set[str], set[str]]] = [
    ("defaults", {}, {"public", "listed", "write_only"}, {"public", "listed", "read_only"}),
    ("exclude", {"exclude": {"listed"}}, {"public", "write_only"}, {"public", "read_only"}),
    (
        "include_all",
        {"include": {"public", "private", "read_only", "write_only", "_under"}},
        {"public", "write_only"},
        {"public", "read_only"},
    ),
    ("include_one", {"include": {"listed"}}, {"listed"}, {"listed"}),
    (
        "underscore_public",
        {"underscore_fields_private": False},
        {"public", "listed", "write_only", "_under"},
        {"public", "listed", "read_only", "_under"},
    ),
    ("exclude_marked", {"exclude": {"read_only", "write_only"}}, {"public", "listed"}, {"public", "listed"}),
]


@pytest.mark.parametrize(
    ("config", "accepted", "returned"),
    [pytest.param(config, accepted, returned, id=label) for label, config, accepted, returned in EXCLUSION_MATRIX],
)
def test_exclusion_matrix(
    config: dict[str, Any], accepted: set[str], returned: set[str], codegen: bool, distinct: Distinct
) -> None:
    dto = DataclassDTO[Annotated[Account, DTOConfig(**config, experimental_codegen_backend=codegen)]]

    @post("/", dto=dto, return_dto=None, sync_to_thread=False)
    @distinct
    def create(data: JSONBody[Account]) -> dict[str, str]:
        return dataclasses.asdict(data)

    @get("/", return_dto=dto, sync_to_thread=False)
    @distinct
    def read() -> Account:
        return Account(**{name: f"v-{name}" for name in ALL_FIELDS})

    with client(create, read) as test_client:
        received = test_client.post("/", json={name: f"sent-{name}" for name in ALL_FIELDS})
        sent = test_client.get("/")

    assert received.status_code == 201
    assert {name for name, value in received.json().items() if value == f"sent-{name}"} == accepted
    assert {name for name, value in received.json().items() if value == f"d-{name.strip('_').replace('_', '-')}"} == (
        ALL_FIELDS - accepted
    )
    assert sent.json() == {name: f"v-{name}" for name in returned}


@dataclass
class Level3:
    name: str = "d3"
    secret: str = "default-3"


@dataclass
class Level2:
    name: str = "d2"
    secret: str = "default-2"
    down: Level3 = field(default_factory=Level3)
    maybe: Level3 | None = None
    many: list[Level3] = field(default_factory=list)


@dataclass
class Level1:
    name: str = "d1"
    secret: str = "default-1"
    down: Level2 = field(default_factory=Level2)
    maybe: Level2 | None = None
    many: list[Level2] = field(default_factory=list)


@dataclass
class Level0:
    name: str = "d0"
    secret: str = "default-0"
    down: Level1 = field(default_factory=Level1)
    maybe: Level1 | None = None
    many: list[Level1] = field(default_factory=list)


def _deep(prefix: str) -> Level0:
    def level3() -> Level3:
        return Level3("n3", f"{prefix}-3")

    def level2() -> Level2:
        return Level2("n2", f"{prefix}-2", level3(), level3(), [level3()])

    def level1() -> Level1:
        return Level1("n1", f"{prefix}-1", level2(), level2(), [level2()])

    return Level0("n0", f"{prefix}-0", level1(), level1(), [level1()])


def _truncated(value: Any, depth: int) -> Any:
    if isinstance(value, list):
        return [_truncated(item, depth) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: _truncated(item, depth - 1)
        for key, item in value.items()
        if depth > 0 or key not in {"down", "maybe", "many"}
    }


def _received(sent: dict[str, Any], default: dict[str, Any], depth: int) -> dict[str, Any]:
    if "down" not in sent:
        return sent
    if depth == 0:
        return {**sent, "down": default["down"], "maybe": None, "many": []}
    nested = default["down"]
    return {
        **sent,
        "down": _received(sent["down"], nested, depth - 1),
        "maybe": _received(sent["maybe"], nested, depth - 1),
        "many": [_received(item, nested, depth - 1) for item in sent["many"]],
    }


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_fields_beyond_max_nested_depth_are_absent_from_responses(
    depth: int, codegen: bool, distinct: Distinct
) -> None:
    dto = DataclassDTO[Annotated[Level0, DTOConfig(max_nested_depth=depth, experimental_codegen_backend=codegen)]]

    @get("/", return_dto=dto, sync_to_thread=False)
    @distinct
    def read() -> Level0:
        return _deep("leak")

    with client(read) as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert response.json() == _truncated(msgspec.to_builtins(_deep("leak")), depth)


@pytest.mark.parametrize("depth", [0, 1, 2, 3])
def test_fields_beyond_max_nested_depth_are_ignored_in_requests(depth: int, codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[Level0, DTOConfig(max_nested_depth=depth, experimental_codegen_backend=codegen)]]

    @post("/", dto=dto, return_dto=None, sync_to_thread=False)
    @distinct
    def create(data: JSONBody[Level0]) -> dict[str, Any]:
        return dataclasses.asdict(data)

    with client(create) as test_client:
        response = test_client.post("/", json=msgspec.to_builtins(_deep("sent")))

    assert response.status_code == 201
    assert response.json() == _received(dataclasses.asdict(_deep("sent")), dataclasses.asdict(Level0()), depth)
    assert {int(level) for level in re.findall(r"sent-(\d)", response.text)} == set(range(depth + 1))


@dataclass
class Leaf:
    name: str


@dataclass
class Branch:
    leaf: Leaf


@dataclass
class Fork:
    leaf: Leaf
    branch: Branch


def test_max_nested_depth_is_cut_per_path(codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[Fork, DTOConfig(experimental_codegen_backend=codegen)]]

    @get("/", return_dto=dto, sync_to_thread=False)
    @distinct
    def read() -> Fork:
        return Fork(leaf=Leaf("near"), branch=Branch(leaf=Leaf("far")))

    with client(read) as test_client:
        assert test_client.get("/").json() == {"leaf": {"name": "near"}, "branch": {}}


@dataclass
class User:
    name: str
    age: int = 0


@dataclass
class Envelope(Generic[T]):
    data: T
    count: int


def test_generic_wrapper_encoding_replaces_the_wrapped_attribute(codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[User, DTOConfig(exclude={"age"}, experimental_codegen_backend=codegen)]]
    returned = Envelope(data=User("a", 1), count=1)

    @get("/", return_dto=dto, sync_to_thread=False)
    @distinct
    def read() -> Envelope[User]:
        return returned

    with client(read) as test_client:
        assert test_client.get("/").json() == {"data": {"name": "a"}, "count": 1}

    replaced: Any = returned.data
    assert isinstance(replaced, msgspec.Struct)
    assert msgspec.to_builtins(replaced) == {"name": "a"}


def test_generic_wrapper_as_data_decodes_the_inner_model(codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[User, DTOConfig(exclude={"age"}, experimental_codegen_backend=codegen)]]

    @post("/", dto=dto, return_dto=None, sync_to_thread=False)
    @distinct
    def create(data: JSONBody[Envelope[User]]) -> str:
        return type(data).__name__

    with client(create) as test_client:
        wrapped = test_client.post("/", json={"data": {"name": "a"}, "count": 1})
        bare = test_client.post("/", json={"name": "a"})

    assert wrapped.status_code == 400
    assert (bare.status_code, bare.text) == (201, "User")


def test_response_wrapper_keeps_status_and_headers(codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[User, DTOConfig(exclude={"age"}, experimental_codegen_backend=codegen)]]

    @get("/one", return_dto=dto, sync_to_thread=False)
    @distinct
    def one() -> Response[User]:
        return Response(User("a", 1), status_code=202, headers={"x-kept": "yes"})

    @get("/many", return_dto=dto, sync_to_thread=False)
    @distinct
    def many() -> Response[list[User]]:
        return Response([User("a", 1), User("b", 2)])

    with client(one, many) as test_client:
        single = test_client.get("/one")
        several = test_client.get("/many")

    assert (single.status_code, single.headers["x-kept"], single.json()) == (202, "yes", {"name": "a"})
    assert several.json() == [{"name": "a"}, {"name": "b"}]


def test_msgpack_payload_is_decoded_for_a_json_body(codegen: bool, distinct: Distinct) -> None:
    dto = DataclassDTO[Annotated[User, DTOConfig(exclude={"age"}, experimental_codegen_backend=codegen)]]

    @post("/", dto=dto, return_dto=None, sync_to_thread=False)
    @distinct
    def create(data: JSONBody[User]) -> dict[str, Any]:
        return dataclasses.asdict(data)

    with client(create) as test_client:
        as_msgpack = test_client.post(
            "/",
            content=msgspec.msgpack.encode({"name": "a", "age": 5}),
            headers={"content-type": "application/vnd.msgpack"},
        )
        as_json = test_client.post("/", json={"name": "a", "age": 5})
        json_as_msgpack = test_client.post(
            "/", content=b'{"name": "a"}', headers={"content-type": "application/vnd.msgpack"}
        )

    assert (as_msgpack.status_code, as_msgpack.json()) == (201, {"name": "a", "age": 0})
    assert (as_json.status_code, as_json.json()) == (201, {"name": "a", "age": 0})
    assert json_as_msgpack.status_code == 400


@dataclass
class Address:
    street: str
    city: str = "c"


@dataclass
class Person:
    name: str
    address: Address
    age: int = 0
    previous: list[Address] = field(default_factory=list)


PERSON_BODY = {"name": "a", "age": 5, "address": {"street": "s"}, "previous": [{"street": "p"}]}


def _describe(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "$model": type(value).__name__,
            **{f.name: _describe(getattr(value, f.name)) for f in dataclasses.fields(value)},
        }
    if isinstance(value, dict):
        return {key: _describe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_describe(item) for item in value]
    return value


def _dto_data_client(
    codegen: bool, distinct: Distinct, use: Callable[[DTOData[Person]], Any], **config: Any
) -> TestClient[Litestar]:
    dto = DataclassDTO[Annotated[Person, DTOConfig(**config, experimental_codegen_backend=codegen)]]

    @patch("/", dto=dto, return_dto=None, sync_to_thread=False)
    @distinct
    def update(data: JSONBody[DTOData[Person]]) -> Any:
        return _describe(use(data))

    return client(update)


def test_dto_data_as_builtins(codegen: bool, distinct: Distinct) -> None:
    with _dto_data_client(codegen, distinct, lambda data: data.as_builtins(), exclude={"age"}) as test_client:
        response = test_client.patch("/", json=PERSON_BODY)

    assert response.json() == {
        "name": "a",
        "address": {"street": "s", "city": "c"},
        "previous": [{"$model": "Address", "street": "p", "city": "c"}],
    }


def test_dto_data_create_instance(codegen: bool, distinct: Distinct) -> None:
    with _dto_data_client(
        codegen, distinct, lambda data: data.create_instance(age=7, address__city="x"), exclude={"age"}
    ) as test_client:
        response = test_client.patch("/", json=PERSON_BODY)

    assert response.json() == {
        "$model": "Person",
        "name": "a",
        "address": {"$model": "Address", "street": "s", "city": "x"},
        "age": 7,
        "previous": [{"$model": "Address", "street": "p", "city": "c"}],
    }


def test_dto_data_update_instance(codegen: bool, distinct: Distinct) -> None:
    def use(data: DTOData[Person]) -> Person:
        return data.update_instance(Person(name="old", address=Address("old"), age=1), age=9)

    with _dto_data_client(codegen, distinct, use, partial=True) as test_client:
        only_name = test_client.patch("/", json={"name": "new"})
        with_address = test_client.patch("/", json={"address": {"street": "s"}})

    assert only_name.json() == {
        "$model": "Person",
        "name": "new",
        "address": {"$model": "Address", "street": "old", "city": "c"},
        "age": 9,
        "previous": [],
    }
    assert with_address.json() == {
        "$model": "Person",
        "name": "old",
        "address": {"street": "s"},
        "age": 9,
        "previous": [],
    }


def test_dto_data_partial_keeps_only_sent_fields(codegen: bool, distinct: Distinct) -> None:
    with _dto_data_client(codegen, distinct, lambda data: data.as_builtins(), partial=True) as test_client:
        empty = test_client.patch("/", json={})
        nested = test_client.patch("/", json={"address": {"city": "x"}})
        invalid = test_client.patch("/", json={"age": "x"})

    assert (empty.status_code, empty.json()) == (200, {})
    assert (nested.status_code, nested.json()) == (200, {"address": {"city": "x"}})
    assert invalid.status_code == 400


def test_dto_data_uses_model_field_names_for_renamed_fields(codegen: bool, distinct: Distinct) -> None:
    with _dto_data_client(
        codegen, distinct, lambda data: data.as_builtins(), rename_strategy="upper", include={"name", "age"}
    ) as test_client:
        response = test_client.patch("/", json={"NAME": "a", "AGE": 3})

    assert response.json() == {"name": "a", "age": 3}
