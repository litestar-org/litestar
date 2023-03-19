from __future__ import annotations

from dataclasses import fields

from examples.data_transfer_objects.dto_mark_fields import Company, CompanyDTO
from starlite.dto.config import DTO_FIELD_META_KEY


def test_company_id_field_mark() -> None:
    dc_fields = fields(Company)
    dto_field = dc_fields[0].metadata[DTO_FIELD_META_KEY]
    assert dto_field.mark == "read-only"


def test_company_super_secret_field_mark() -> None:
    dc_fields = fields(Company)
    dto_field = dc_fields[-1].metadata[DTO_FIELD_META_KEY]
    assert dto_field.mark == "private"


def test_company_dto_field_definitions() -> None:
    CompanyDTO.postponed_cls_init()
    assert CompanyDTO.config.purpose == "write"
    assert "id" not in CompanyDTO.field_definitions
    assert "super_secret" not in CompanyDTO.field_definitions
