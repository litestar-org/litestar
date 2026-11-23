from __future__ import annotations

import pytest

from litestar.dto.field import DTO_FIELD_META_KEY, DTOField, Mark, extract_dto_field
from litestar.exceptions import ImproperlyConfiguredException
from litestar.typing import FieldDefinition


def test_extract_dto_field_unexpected_type() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        extract_dto_field(FieldDefinition.from_annotation(int), {DTO_FIELD_META_KEY: object()})


@pytest.mark.parametrize(
    "literal, member", [("private", Mark.PRIVATE), ("read-only", Mark.READ_ONLY), ("write-only", Mark.WRITE_ONLY)]
)
def test_dto_field_converts_string_mark(literal: str, member: Mark) -> None:
    assert DTOField(mark=literal).mark is member  # type: ignore[arg-type]
    assert DTOField(mark=member).mark is member
    assert DTOField().mark is None


def test_dto_field_rejects_unknown_mark() -> None:
    with pytest.raises(ValueError, match="bogus"):
        DTOField(mark="bogus")  # type: ignore[arg-type]
