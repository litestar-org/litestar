from __future__ import annotations

from typing import TYPE_CHECKING, List

import pytest

from starlite.dto.backends.msgspec import MsgspecDTOBackend
from starlite.dto.backends.pydantic import PydanticDTOBackend
from starlite.dto.types import FieldDefinition
from starlite.enums import MediaType

if TYPE_CHECKING:
    from starlite.dto.backends.abc import AbstractDTOBackend
    from starlite.dto.types import FieldDefinitionsType


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_dto_backends(backend_type: type[AbstractDTOBackend]) -> None:
    field_definitions: FieldDefinitionsType = {
        "a": FieldDefinition(field_name="a", field_type=int),
        "b": FieldDefinition(field_name="b", field_type=str, default="b"),
        "c": FieldDefinition(field_name="c", field_type=List[int], default_factory=list),
    }
    backend = backend_type.from_field_definitions(type, field_definitions)
    assert backend.parse_raw(b'{"a":1}', media_type=MediaType.JSON) == {"a": 1, "b": "b", "c": []}
