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
    CompanyDTO.postponed_cls_init()
    fields = CompanyDTO.field_definitions
    assert fields["id"].field_type is int
    assert fields["name"].field_type is str
    assert fields["worth"].field_type is float


def test_dto_add_new_fields() -> None:
    AddFieldClassDTO.postponed_cls_init()
    fields = AddFieldClassDTO.field_definitions

    assert fields["third"].field_type is str


def test_dto_exclude_fields() -> None:
    ExcludeFieldClassDTO.postponed_cls_init()
    fields = ExcludeFieldClassDTO.field_definitions

    assert "first" not in fields


def test_dto_remap_fields() -> None:
    RemapClassDTO.postponed_cls_init()
    fields = RemapClassDTO.field_definitions

    assert "first" not in fields
    assert fields["third"].field_type is int


def test_dto_remap_fields_with_types() -> None:
    RemapWithTypesClassDTO.postponed_cls_init()
    fields = RemapWithTypesClassDTO.field_definitions

    assert "first" not in fields
    assert "second" not in fields

    assert fields["third"].field_type is int
    assert fields["fourth"].field_type is float
