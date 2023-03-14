from pydantic import BaseModel

from examples.data_transfer_objects.dto_add_new_fields import (
    MyClassDTO as AddFieldClassDTO,
)
from examples.data_transfer_objects.dto_basic import CompanyDTO
from examples.data_transfer_objects.dto_exclude_fields import (
    MyClassDTO as ExcludeFieldClassDTO,
)
from examples.data_transfer_objects.dto_remap_fields import MyClassDTO as RemapClassDTO
from examples.data_transfer_objects.dto_remap_fields_with_types import (
    MyClassDTO as RemapWithTypesClassDTO,
)


def test_dto_creation() -> None:
    assert issubclass(CompanyDTO, BaseModel)

    fields = CompanyDTO.__fields__
    assert fields["id"].type_ is int
    assert fields["name"].type_ is str
    assert fields["worth"].type_ is float


def test_dto_add_new_fields() -> None:
    fields = AddFieldClassDTO.__fields__

    assert fields["third"].type_ is str


def test_dto_exclude_fields() -> None:
    fields = ExcludeFieldClassDTO.__fields__

    assert "first" not in fields


def test_dto_remap_fields() -> None:
    fields = RemapClassDTO.__fields__

    assert "first" not in fields
    assert fields["third"].type_ is int


def test_dto_remap_fields_with_types() -> None:
    fields = RemapWithTypesClassDTO.__fields__

    assert "first" not in fields
    assert "second" not in fields

    assert fields["third"].type_ is int
    assert fields["fourth"].type_ is float
