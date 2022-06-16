import sys
from typing import Any, Dict, List, Type, cast

import pytest
from pydantic import BaseModel, create_model
from pydantic_factories import ModelFactory
from starlette.status import HTTP_200_OK, HTTP_201_CREATED

from starlite import (
    DTOFactory,
    ImproperlyConfiguredException,
    Starlite,
    create_test_client,
    get,
    post,
)
from starlite.plugins.sql_alchemy import SQLAlchemyPlugin
from tests import Person
from tests import Pet as PydanticPet
from tests import Species, VanillaDataClassPerson
from tests.plugins.sql_alchemy_plugin import Pet, User


@pytest.mark.parametrize(
    "model, exclude, field_mapping, field_definitions, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, {"special": (str, ...)}, []],
        [Pet, ["age"], {"species": "kind"}, {"special": (str, ...)}, [SQLAlchemyPlugin()]],
    ],
)
def test_dto_factory(model: Any, exclude: list, field_mapping: dict, field_definitions: dict, plugins: list) -> None:
    dto = DTOFactory(plugins=plugins)(
        "MyDTO", model, exclude=exclude, field_mapping=field_mapping, field_definitions=field_definitions
    )
    assert issubclass(dto, BaseModel)
    assert dto.__name__ == "MyDTO"
    assert not any(excluded_key in dto.__fields__ for excluded_key in exclude)
    assert all(remapped_key in dto.__fields__ for remapped_key in field_mapping.values())
    special = dto.__fields__["special"]
    assert not special.allow_none
    assert special.type_ is str


def test_dto_factory_type_remap() -> None:
    dto = DTOFactory(plugins=[])(
        "PersonDTO", Person, field_mapping={"id": ("id", int), "optional": ("required", str), "complex": "simple"}
    )
    assert issubclass(dto, BaseModel)
    fields = dto.__fields__
    assert fields["id"].type_ is int
    assert fields["required"].type_ is str
    assert fields["simple"].type_ == Person.__fields__["complex"].type_


def test_dto_factory_handle_of_default_values() -> None:
    dto = DTOFactory(plugins=[])("PetFactory", PydanticPet)
    assert issubclass(dto, BaseModel)
    fields = dto.__fields__
    assert fields["species"].default is Species.MONKEY


def test_dto_factory_validation() -> None:
    class MyClass:
        name: str

    with pytest.raises(ImproperlyConfiguredException):
        DTOFactory(plugins=[])("MyDTO", MyClass)


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [Pet, ["owner"], {"species": "kind"}, [SQLAlchemyPlugin()]],
    ],
)
def test_dto_integration(model: Any, exclude: list, field_mapping: dict, plugins: list) -> None:
    MyDTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    class DTOModelFactory(ModelFactory[MyDTO]):  # type: ignore
        __model__ = MyDTO

    dto_instance = DTOModelFactory.build().dict()  # type: ignore

    @post(path="/")
    def post_handler(data: MyDTO) -> None:  # type: ignore
        assert isinstance(data, MyDTO)
        assert data == dto_instance

    @get(path="/")
    def get_handler() -> Any:
        return dto_instance

    with create_test_client(route_handlers=[post_handler, get_handler]) as client:
        post_response = client.post("/", json=dto_instance)
        assert post_response.status_code == HTTP_201_CREATED
        get_response = client.get("/")
        assert get_response.status_code == HTTP_200_OK
        assert get_response.json() == dto_instance


def test_dto_openapi_generation() -> None:
    SQLAlchemyDTOFactory = DTOFactory(plugins=[SQLAlchemyPlugin()])

    UserCreateDTO = SQLAlchemyDTOFactory(
        "UserCreateDTO",
        User,
        field_mapping={"hashed_password": ("password", str)},
    )

    UserReadDTO = SQLAlchemyDTOFactory("UserRead", User, exclude=["hashed_password"])

    @get(path="/user")
    def get_user() -> UserReadDTO:  # type: ignore
        ...

    @post(path="/user")
    def create_user(data: UserCreateDTO) -> UserReadDTO:  # type: ignore
        ...

    app = Starlite(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert app.openapi_schema


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, [], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, [], {"complex": "ultra"}, []],
        [Pet, ["age"], {"species": "kind"}, [SQLAlchemyPlugin()]],
    ],
)
def test_conversion_to_model_instance(model: Any, exclude: list, field_mapping: dict, plugins: list) -> None:
    MyDTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    class DTOModelFactory(ModelFactory[MyDTO]):  # type: ignore
        __model__ = MyDTO
        __allow_none_optionals__ = False

    dto_instance = DTOModelFactory.build()
    model_instance = dto_instance.to_model_instance()  # type: ignore

    for key in dto_instance.__fields__:  # type: ignore
        if key not in MyDTO.dto_field_mapping:
            assert model_instance.__getattribute__(key) == dto_instance.__getattribute__(key)  # type: ignore
        else:
            original_key = MyDTO.dto_field_mapping[key]
            assert model_instance.__getattribute__(original_key) == dto_instance.__getattribute__(key)  # type: ignore


@pytest.mark.skipif(sys.version_info < (3, 9), reason="dataclasses behave differently in lower versions")
@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [Pet, ["age"], {"species": "kind"}, [SQLAlchemyPlugin()]],
    ],
)
def test_conversion_from_model_instance(
    model: Any, exclude: List[Any], field_mapping: Dict[str, Any], plugins: List[Any]
) -> None:
    DTO = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    if issubclass(model, (Person, VanillaDataClassPerson)):
        model_instance = model(
            first_name="moishe",
            last_name="zuchmir",
            id=1,
            optional="some-value",
            complex={"key": [{"key": "value"}]},
            pets=None,
        )
    else:
        model_instance = cast(Type[Pet], model)(  # type: ignore[call-arg]
            id=1,
            species=Species.MONKEY,
            name="Mike",
            age=3,
            owner_id=1,
        )
    dto_instance = DTO.from_model_instance(model_instance=model_instance)
    for key in dto_instance.__fields__:
        if key not in DTO.dto_field_mapping:
            assert model_instance.__getattribute__(key) == dto_instance.__getattribute__(key)
        else:
            original_key = DTO.dto_field_mapping[key]
            assert model_instance.__getattribute__(original_key) == dto_instance.__getattribute__(key)


def test_dto_factory_preserves_field_allow_none_false() -> None:
    Example = create_model("Example", password=(str, ...))
    assert Example.__fields__["password"].allow_none is False
    ExampleDTO = DTOFactory()("ExampleDTO", Example)
    assert ExampleDTO.__fields__["password"].allow_none is False


def test_dto_factory_preserves_field_info_where_unnecessary_to_change() -> None:
    ExampleDTO = DTOFactory(plugins=[])("ExampleDTO", PydanticPet, exclude=[], field_mapping={}, field_definitions={})
    assert PydanticPet.__fields__["name"].field_info is ExampleDTO.__fields__["name"].field_info
