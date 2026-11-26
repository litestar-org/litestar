from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any, Generic, Optional, TypeVar

import pytest

from litestar import Controller, Litestar, get, patch, post, put
from litestar.dto import DataclassDTO, DTOConfig, DTOData, dto_field
from litestar.exceptions import ImproperlyConfiguredException
from litestar.handlers import HTTPRouteHandler
from litestar.params import JSONBody
from litestar.typing import FieldDefinition


@dataclass
class Address:
    street: str = ""
    city: str = ""


@dataclass
class User:
    id: int = 0
    name: str = ""
    secret: str = ""


@dataclass
class Admin(User):
    level: int = 0


@dataclass
class Customer:
    id: int = 0
    billing: Address = field(default_factory=Address)
    shipping: Address = field(default_factory=Address)
    previous: list[Address] = field(default_factory=list)


@dataclass
class Node:
    id: int = 0
    parent: Optional["Node"] = None
    children: list["Node"] = field(default_factory=list)


@dataclass
class Cafe:
    id: int = 0
    address: Address = field(default_factory=Address)


Cafe.__name__ = "Zoë"


@dataclass
class snake_case_model:
    id: int = 0


@dataclass
class Unicode:
    größe: Address = field(default_factory=Address)  # noqa: PLC2401
    grösse: Address = field(default_factory=Address)  # noqa: PLC2401


@dataclass
class Account:
    name: str = ""
    id: int = field(default=0, metadata=dto_field("read-only"))


@dataclass
class Holder:
    name: str = ""
    account: Account = field(default_factory=Account)


@dataclass
class UsersItem:
    x: int = 0


@dataclass
class ItemsItem:
    x: int = 0


UsersItem.__module__, ItemsItem.__module__ = "users", "items"
UsersItem.__name__ = UsersItem.__qualname__ = ItemsItem.__name__ = ItemsItem.__qualname__ = "Item"


@dataclass
class Credentials:
    name: str = ""
    password: str = field(default="", metadata=dto_field("write-only"))


class UserDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"secret"})


class UserPublicDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"secret", "id"})


class UserPatchDTO(DataclassDTO[User]):
    config = DTOConfig(exclude={"id"}, partial=True)


class CustomerDTO(DataclassDTO[Customer]):
    config = DTOConfig()


class NodeDTO(DataclassDTO[Node]):
    config = DTOConfig(max_nested_depth=2)


class CafeDTO(DataclassDTO[Cafe]):
    config = DTOConfig()


class SnakeDTO(DataclassDTO[snake_case_model]):
    config = DTOConfig()


class UniDTO(DataclassDTO[Unicode]):
    config = DTOConfig()


class NamedCustomerDTO(DataclassDTO[Customer]):
    __schema_name__ = "CustomerOut"
    config = DTOConfig()


class AccountDTO(DataclassDTO[Account]):
    __schema_name__ = "Account"


class CredentialsDTO(DataclassDTO[Credentials]):
    __schema_name__ = "Credentials"


class HolderDTO(DataclassDTO[Holder]):
    __schema_name__ = "Holder"
    config = DTOConfig(exclude={"account"})


def one_handler() -> list[HTTPRouteHandler]:
    @get("/u", return_dto=UserDTO)
    async def get_user() -> User:
        return User()

    return [get_user]


def same_dto_on_several_handlers() -> list[HTTPRouteHandler]:
    @get("/u", return_dto=UserDTO)
    async def get_user() -> User:
        return User()

    @get("/us", return_dto=UserDTO)
    async def list_users() -> list[User]:
        return []

    @get("/u2", return_dto=UserDTO)
    async def other_user() -> User:
        return User()

    return [get_user, list_users, other_user]


def request_and_response() -> list[HTTPRouteHandler]:
    @post("/u", dto=UserDTO)
    async def create_user(data: JSONBody[User]) -> User:
        return data

    return [create_user]


def two_dtos_over_one_model() -> list[HTTPRouteHandler]:
    @post("/u", dto=UserPublicDTO, return_dto=UserDTO)
    async def create_user(data: JSONBody[User]) -> User:
        return data

    @get("/u", return_dto=UserPublicDTO)
    async def get_user() -> User:
        return User()

    @get("/u2", return_dto=UserDTO)
    async def get_user2() -> User:
        return User()

    return [create_user, get_user, get_user2]


def nested_by_two_paths_and_in_a_list() -> list[HTTPRouteHandler]:
    @get("/c", return_dto=CustomerDTO)
    async def get_customer() -> Customer:
        return Customer()

    return [get_customer]


def self_reference() -> list[HTTPRouteHandler]:
    @get("/n", return_dto=NodeDTO)
    async def get_node() -> Node:
        return Node()

    return [get_node]


def partial() -> list[HTTPRouteHandler]:
    @patch("/u", dto=UserPatchDTO, return_dto=UserDTO)
    async def patch_user(data: JSONBody[User]) -> User:
        return data

    return [patch_user]


def unusual_class_names() -> list[HTTPRouteHandler]:
    @get("/c", return_dto=CafeDTO)
    async def get_cafe() -> Cafe:
        return Cafe()

    @get("/a", return_dto=DataclassDTO[Cafe])
    async def get_anonymous_cafe() -> Cafe:
        return Cafe()

    @get("/s", return_dto=SnakeDTO)
    async def get_snake_thing() -> snake_case_model:
        return snake_case_model()

    @get("/x", return_dto=UniDTO)
    async def uni() -> Unicode:
        return Unicode()

    return [get_cafe, get_anonymous_cafe, get_snake_thing, uni]


def model_subclass() -> list[HTTPRouteHandler]:
    @get("/u", return_dto=UserDTO)
    async def get_user() -> User:
        return User()

    @get("/a", return_dto=UserDTO)
    async def get_admin() -> Admin:
        return Admin()

    return [get_user, get_admin]


def schema_name_with_same_fields_in_both_directions() -> list[HTTPRouteHandler]:
    @post("/c", dto=NamedCustomerDTO)
    async def create(data: JSONBody[Customer]) -> Customer:
        return data

    @get("/c", return_dto=NamedCustomerDTO)
    async def read() -> Customer:
        return Customer()

    return [create, read]


def schema_name_with_directional_field_under_excluded_parent() -> list[HTTPRouteHandler]:
    @post("/h", dto=HolderDTO, return_dto=HolderDTO)
    async def create(data: JSONBody[Holder]) -> Holder:
        return data

    return [create]


def component_names(handlers: list[Any]) -> list[str]:
    return sorted(Litestar(handlers).openapi_schema.components.schemas)


def transfer_models(app: Litestar) -> set[type[Any]]:
    return {
        backend.transfer_model_type
        for route in app.routes
        for handler in getattr(route, "route_handler_map", {}).values()
        for backend in (handler._dto_data_backend, handler._dto_return_backend)
        if backend is not None
    }


@pytest.mark.parametrize(
    ("make_handlers", "expected"),
    [
        (one_handler, ["UserDTOResponseBody"]),
        (same_dto_on_several_handlers, ["UserDTOResponseBody"]),
        (request_and_response, ["UserDTORequestBody", "UserDTOResponseBody"]),
        (two_dtos_over_one_model, ["UserDTOResponseBody", "UserPublicDTORequestBody", "UserPublicDTOResponseBody"]),
        (
            nested_by_two_paths_and_in_a_list,
            [
                "CustomerDTOResponseBody",
                "CustomerDTOResponseBody.billing",
                "CustomerDTOResponseBody.previous",
                "CustomerDTOResponseBody.shipping",
            ],
        ),
        (
            self_reference,
            [
                "NodeDTOResponseBody",
                "NodeDTOResponseBody.children",
                "NodeDTOResponseBody.children.children",
                "NodeDTOResponseBody.children.parent",
                "NodeDTOResponseBody.parent",
                "NodeDTOResponseBody.parent.children",
                "NodeDTOResponseBody.parent.parent",
            ],
        ),
        (partial, ["UserDTOResponseBody", "UserPatchDTORequestBody"]),
        (
            unusual_class_names,
            [
                "CafeDTOResponseBody",
                "CafeDTOResponseBody.address",
                "SnakeDTOResponseBody",
                "UniDTOResponseBody",
                "UniDTOResponseBody.gr_f6_dfe",
                "UniDTOResponseBody.gr_f6sse",
                "Zo_ebResponseBody",
                "Zo_ebResponseBody.address",
            ],
        ),
        (model_subclass, ["UserDTOAdminResponseBody", "UserDTOResponseBody"]),
        (
            schema_name_with_same_fields_in_both_directions,
            ["CustomerOut", "CustomerOut.billing", "CustomerOut.previous", "CustomerOut.shipping"],
        ),
        (schema_name_with_directional_field_under_excluded_parent, ["Holder"]),
    ],
)
def test_component_names(make_handlers: Callable[[], list[HTTPRouteHandler]], expected: list[str]) -> None:
    assert component_names(make_handlers()) == expected


@pytest.mark.parametrize(
    ("make_handlers", "expected_models"),
    [
        (same_dto_on_several_handlers, 1),
        (request_and_response, 2),
        (two_dtos_over_one_model, 3),
        (schema_name_with_same_fields_in_both_directions, 1),
        (schema_name_with_directional_field_under_excluded_parent, 1),
    ],
)
def test_handlers_with_the_same_dto_share_one_transfer_model(
    make_handlers: Callable[[], list[HTTPRouteHandler]], expected_models: int
) -> None:
    assert len(transfer_models(Litestar(make_handlers()))) == expected_models


def test_two_applications_do_not_share_transfer_models() -> None:
    handlers = one_handler()
    first, second = Litestar(handlers), Litestar(handlers)

    assert sorted(first.openapi_schema.components.schemas) == ["UserDTOResponseBody"]
    assert sorted(second.openapi_schema.components.schemas) == ["UserDTOResponseBody"]
    assert transfer_models(first).isdisjoint(transfer_models(second))


def test_unrelated_handler_with_a_clashing_function_name_leaves_names_unchanged() -> None:
    class OtherController(Controller):
        path = "/other"

        @get(return_dto=UserPublicDTO)
        async def get_user(self) -> User:
            return User()

    names = component_names(one_handler())

    assert set(names) < set(component_names([*one_handler(), OtherController]))
    assert component_names([OtherController, *one_handler()]) == component_names([*one_handler(), OtherController])


def schema_name_with_read_only_field() -> list[HTTPRouteHandler]:
    @post("/a", dto=AccountDTO)
    async def create(data: JSONBody[Account]) -> Account:
        return data

    return [create]


def schema_name_with_write_only_field() -> list[HTTPRouteHandler]:
    @post("/c", dto=CredentialsDTO)
    async def create(data: JSONBody[Credentials]) -> Credentials:
        return data

    @get("/c", return_dto=CredentialsDTO)
    async def read() -> Credentials:
        return Credentials()

    return [create, read]


def schema_name_with_read_only_field_request_only() -> list[HTTPRouteHandler]:
    @post("/a", dto=AccountDTO, return_dto=None)
    async def create(data: JSONBody[Account]) -> None:
        return None

    return [create]


def anonymous_dtos_over_one_model_with_different_configs() -> list[HTTPRouteHandler]:
    @post("/u", dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"id"})]], return_dto=None)
    async def create(data: JSONBody[User]) -> None:
        return None

    @put("/u", dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"id"})]], return_dto=None)
    async def replace(data: JSONBody[User]) -> None:
        return None

    @patch("/u", dto=DataclassDTO[Annotated[User, DTOConfig(partial=True)]], return_dto=None)
    async def update(data: JSONBody[DTOData[User]]) -> None:
        return None

    @get("/u", return_dto=DataclassDTO[User])
    async def read() -> User:
        return User()

    return [create, replace, update, read]


def make_read_dto(model: Any, module: str) -> Any:
    class ReadDTO(DataclassDTO[model]):
        config = DTOConfig()

    ReadDTO.__module__ = module
    return ReadDTO


def same_named_dtos_in_two_modules() -> list[HTTPRouteHandler]:
    users_read_dto, items_read_dto = make_read_dto(User, "app.users.dto"), make_read_dto(Customer, "app.items.dto")

    @get("/u", return_dto=users_read_dto)
    async def get_user() -> User:
        return User()

    @get("/c", return_dto=items_read_dto)
    async def get_customer() -> Customer:
        return Customer()

    return [get_user, get_customer]


def anonymous_dtos_over_same_named_models_in_two_modules() -> list[HTTPRouteHandler]:
    @get("/u", return_dto=DataclassDTO[UsersItem])
    async def get_users_item() -> UsersItem:
        return UsersItem()

    @get("/i", return_dto=DataclassDTO[ItemsItem])
    async def get_items_item() -> ItemsItem:
        return ItemsItem()

    return [get_users_item, get_items_item]


LAYOUTS_THAT_WORK_ON_MAIN = [
    (schema_name_with_read_only_field, ["AccountRequestBody", "AccountResponseBody"]),
    (schema_name_with_write_only_field, ["CredentialsRequestBody", "CredentialsResponseBody"]),
    (schema_name_with_read_only_field_request_only, ["AccountRequestBody"]),
    (
        anonymous_dtos_over_one_model_with_different_configs,
        ["UserRequestBody_1d2fc036", "UserRequestBody_fb568797", "UserResponseBody"],
    ),
    (
        same_named_dtos_in_two_modules,
        [
            "ReadDTOResponseBody.billing",
            "ReadDTOResponseBody.previous",
            "ReadDTOResponseBody.shipping",
            "items_dto_ReadDTOResponseBody",
            "users_dto_ReadDTOResponseBody",
        ],
    ),
    (anonymous_dtos_over_same_named_models_in_two_modules, ["items_ItemResponseBody", "users_ItemResponseBody"]),
]


@pytest.mark.parametrize(("make_handlers", "expected"), LAYOUTS_THAT_WORK_ON_MAIN)
def test_names_of_layouts_that_work_on_main(
    make_handlers: Callable[[], list[HTTPRouteHandler]], expected: list[str]
) -> None:
    assert component_names(make_handlers()) == expected


@pytest.mark.parametrize(("make_handlers", "expected"), LAYOUTS_THAT_WORK_ON_MAIN)
def test_names_do_not_depend_on_registration_order(
    make_handlers: Callable[[], list[HTTPRouteHandler]], expected: list[str]
) -> None:
    assert component_names(make_handlers()[::-1]) == expected


def test_anonymous_dto_config_fingerprint_is_stable() -> None:
    @get("/u", return_dto=DataclassDTO[Annotated[User, DTOConfig(exclude={"secret", "id"}, rename_strategy="camel")]])
    async def read() -> User:
        return User()

    assert component_names([read]) == ["UserResponseBody_1e33fe93"]


def test_same_named_dtos_in_one_module_fail_at_startup() -> None:
    first, second = make_read_dto(User, "app.dto"), make_read_dto(Address, "app.dto")

    @get("/u", return_dto=first)
    async def get_user() -> User:
        return User()

    @get("/a", return_dto=second)
    async def get_address() -> Address:
        return Address()

    with pytest.raises(
        ImproperlyConfiguredException,
        match=r"'ReadDTOResponseBody'.*'app\.dto\.make_read_dto\.<locals>\.ReadDTO' and "
        r"'app\.dto\.make_read_dto\.<locals>\.ReadDTO'.*'__schema_name__'",
    ):
        Litestar([get_user, get_address])


def test_backend_without_application_has_the_same_names_and_no_sharing() -> None:
    first, second = (
        UserDTO.create_for_field_definition(FieldDefinition.from_annotation(User), handler_id="h") for _ in range(2)
    )

    assert first.transfer_model_type.__name__ == second.transfer_model_type.__name__
    assert first.transfer_model_type.__name__ == "UserDTOResponseBody"
    assert first.transfer_model_type is not second.transfer_model_type


def test_field_paths_get_distinct_names() -> None:
    @dataclass
    class Leaf:
        x: int = 1

    @dataclass
    class OtherLeaf:
        y: int = 1

    @dataclass
    class Branch:
        b: OtherLeaf = field(default_factory=OtherLeaf)

    @dataclass
    class Root:
        a_b: Leaf = field(default_factory=Leaf)
        a: Branch = field(default_factory=Branch)

    class RootDTO(DataclassDTO[Root]):
        config = DTOConfig(max_nested_depth=2)

    @get("/", return_dto=RootDTO, sync_to_thread=False)
    def handler() -> Root:
        return Root()

    schemas = Litestar([handler]).openapi_schema.components.schemas

    assert {name: sorted(schema.properties or {}) for name, schema in schemas.items()} == {
        "RootDTOResponseBody": ["a", "a_b"],
        "RootDTOResponseBody.a": ["b"],
        "RootDTOResponseBody.a.b": ["y"],
        "RootDTOResponseBody.a_b": ["x"],
    }


T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: list[T]


def test_generic_wrapper_component_is_named_without_module_paths() -> None:
    @get("/", return_dto=UserDTO, sync_to_thread=False)
    def handler() -> Page[User]:
        return Page(items=[])

    schemas = Litestar([handler]).openapi_schema.components.schemas

    assert set(schemas) == {"UserDTOResponseBody", "Page_UserDTOResponseBody_"}
