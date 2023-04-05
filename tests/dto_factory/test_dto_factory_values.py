import pytest
from pydantic import BaseModel, create_model

from litestar.dto import DTOFactory
from litestar.exceptions import ImproperlyConfiguredException
from tests import Person, Species
from tests import Pet as PydanticPet


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


def test_dto_factory_preserves_field_allow_none_false() -> None:
    Example = create_model("Example", password=(str, ...))
    assert Example.__fields__["password"].allow_none is False
    ExampleDTO = DTOFactory()("ExampleDTO", Example)
    assert ExampleDTO.__fields__["password"].allow_none is False


def test_dto_factory_preserves_field_info_where_unnecessary_to_change() -> None:
    ExampleDTO = DTOFactory(plugins=[])("ExampleDTO", PydanticPet, exclude=[], field_mapping={}, field_definitions={})
    assert PydanticPet.__fields__["name"].field_info is ExampleDTO.__fields__["name"].field_info
