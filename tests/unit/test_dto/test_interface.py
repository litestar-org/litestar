from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from litestar.dto import AbstractDTO
from litestar.openapi.spec.schema import Schema
from litestar.typing import FieldDefinition


def test_dto_interface_create_openapi_schema_default_implementation(ModelDataDTO: type[AbstractDTO]) -> None:
    assert (
        ModelDataDTO.create_openapi_schema(FieldDefinition.from_annotation(Any), MagicMock(), MagicMock()) == Schema()
    )
