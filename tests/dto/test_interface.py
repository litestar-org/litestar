from __future__ import annotations

from unittest.mock import MagicMock

from litestar.openapi.spec.schema import Schema

from . import MockDTO


def test_dto_interface_create_openapi_schema_default_implementation() -> None:
    assert MockDTO.create_openapi_schema("data", MagicMock(), False, {}, True) == Schema()
