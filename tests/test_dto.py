from typing import Any

import pytest
from pydantic import BaseModel
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
from tests.plugins.sql_alchemy_plugin import Company, Pet, User


@pytest.mark.parametrize(
    "model, exclude, field_mapping, plugins",
    [
        [Person, ["id"], {"complex": "ultra"}, []],
        [VanillaDataClassPerson, ["id"], {"complex": "ultra"}, []],
        [Pet, ["age"], {"species": "kind"}, [SQLAlchemyPlugin()]],
    ],
)
def test_dto_factory(model: Any, exclude: list, field_mapping: dict, plugins: list):
    dto = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)
    assert issubclass(dto, BaseModel)
    assert dto.__name__ == "MyDTO"
    assert not any(excluded_key in dto.__fields__ for excluded_key in exclude)
    assert all(remapped_key in dto.__fields__ for remapped_key in field_mapping.values())


def test_dto_factory_type_remap():
    dto = DTOFactory(plugins=[])(
        "PersonDTO", Person, field_mapping={"id": ("id", int), "optional": ("required", str), "complex": "simple"}
    )
    assert issubclass(dto, BaseModel)
    fields = dto.__fields__
    assert fields["id"].type_ is int
    assert fields["required"].type_ is str
    assert fields["simple"].type_ == Person.__fields__["complex"].type_


def test_dto_factory_handle_of_default_values():
    dto = DTOFactory(plugins=[])("PetFactory", PydanticPet)
    assert issubclass(dto, BaseModel)
    fields = dto.__fields__
    assert fields["species"].default is Species.MONKEY


def test_dto_factory_validation():
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
def test_dto_integration(model: Any, exclude: list, field_mapping: dict, plugins: list):
    dto = DTOFactory(plugins=plugins)("MyDTO", model, exclude=exclude, field_mapping=field_mapping)

    class DTOModelFactory(ModelFactory):
        __model__ = dto

    dto_instance = DTOModelFactory.build().dict()

    @post(path="/")
    def post_handler(data: dto) -> None:
        assert isinstance(data, dto)
        assert data == dto_instance

    @get(path="/")
    def get_handler() -> dto:
        return dto_instance

    with create_test_client(route_handlers=[post_handler, get_handler]) as client:
        post_response = client.post("/", json=dto_instance)
        assert post_response.status_code == HTTP_201_CREATED
        get_response = client.get("/")
        assert get_response.status_code == HTTP_200_OK
        assert get_response.json() == dto_instance


def test_dto_openapi_generation():
    SQLAlchemyDTOFactory = DTOFactory(plugins=[SQLAlchemyPlugin()])

    UserCreateDTO = SQLAlchemyDTOFactory(
        "UserCreateDTO",
        User,
        field_mapping={"hashed_password": ("password", str)},
    )

    UserReadDTO = SQLAlchemyDTOFactory("UserRead", User, exclude=["hashed_password"])

    @get(path="/user")
    def get_user() -> UserReadDTO:
        ...

    @post(path="/user")
    def create_user(data: UserCreateDTO) -> UserReadDTO:
        ...

    app = Starlite(route_handlers=[get_user, create_user], plugins=[SQLAlchemyPlugin()])
    assert app.openapi_schema


def test_conversion_to_original_class():
    SQLAlchemyDTOFactory = DTOFactory(plugins=[SQLAlchemyPlugin()])

    CompanyDTO = SQLAlchemyDTOFactory(
        "CompanyDTO",
        Company,
        field_mapping={"worth": "value"},
    )

    class CompanyDTOFactory(ModelFactory[CompanyDTO]):
        __model__ = CompanyDTO

    dto_instance = CompanyDTOFactory.build()

    company_instance = dto_instance.to_model_instance()

    assert dto_instance.value
    assert company_instance.worth == dto_instance.value
