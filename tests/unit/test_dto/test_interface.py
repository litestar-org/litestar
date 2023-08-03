from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from litestar.openapi.spec.schema import Schema
from litestar.typing import FieldDefinition

from . import TestModelDataDTO


def test_dto_interface_create_openapi_schema_default_implementation() -> None:
    assert (
        TestModelDataDTO.create_openapi_schema(FieldDefinition.from_annotation(Any), MagicMock(), MagicMock())
        == Schema()
    )
