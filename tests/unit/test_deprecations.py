import importlib

import pytest


@pytest.mark.parametrize(
    "module_name, member_name",
    (
        ("litestar.dto.factory", "AbstractDTOFactory"),
        ("litestar.dto.factory", "DataclassDTO"),
        ("litestar.dto.factory", "DTOConfig"),
        ("litestar.dto.factory", "DTOField"),
        ("litestar.dto.factory", "DTOData"),
        ("litestar.dto.factory", "DTOConfig"),
        ("litestar.dto.factory", "DTOField"),
        ("litestar.dto.factory", "Mark"),
        ("litestar.dto.factory", "dto_field"),
        ("litestar.dto.factory.stdlib.dataclass", "DataclassDTO"),
        ("litestar.contrib.msgspec", "MsgspecDTO"),
    ),
)
def test_deprecated_modules(module_name: str, member_name: str) -> None:
    try:
        module = importlib.import_module(module_name)
        assert module.__getattr__(member_name)
    except ImportError as e:
        raise AssertionError from e
