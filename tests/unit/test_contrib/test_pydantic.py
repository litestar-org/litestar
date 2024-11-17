# ruff: noqa: TCH004, F401
from __future__ import annotations

import importlib
import sys
from importlib.util import cache_from_source
from pathlib import Path

import pytest


def purge_module(module_names: list[str], path: str | Path) -> None:
    for name in module_names:
        if name in sys.modules:
            del sys.modules[name]
    Path(cache_from_source(str(path))).unlink(missing_ok=True)


def test_deprecated_pydantic_imports() -> None:
    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(DeprecationWarning, match="importing PydanticDTO from 'litestar.contrib.pydantic' is deprecated"):
        from litestar.contrib.pydantic import PydanticDTO

    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PydanticInitPlugin from 'litestar.contrib.pydantic' is deprecated"
    ):
        from litestar.contrib.pydantic import PydanticInitPlugin

    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PydanticSchemaPlugin from 'litestar.contrib.pydantic' is deprecated"
    ):
        from litestar.contrib.pydantic import PydanticSchemaPlugin

    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PydanticPlugin from 'litestar.contrib.pydantic' is deprecated"
    ):
        from litestar.contrib.pydantic import PydanticPlugin

    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(
        DeprecationWarning, match="importing PydanticDIPlugin from 'litestar.contrib.pydantic' is deprecated"
    ):
        from litestar.contrib.pydantic import PydanticDIPlugin


def test_deprecated_pydantic_dto_factory_imports() -> None:
    purge_module(["litestar.contrib.pydantic.pydantic_dto_factory"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PydanticDTO from 'litestar.contrib.pydantic' is deprecated",
    ):
        from litestar.contrib.pydantic import PydanticDTO


def test_deprecated_pydantic_init_plugin_imports() -> None:
    purge_module(["litestar.contrib.pydantic.pydantic_init_plugin"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PydanticInitPlugin from 'litestar.contrib.pydantic' is deprecated",
    ):
        from litestar.contrib.pydantic import PydanticInitPlugin


def test_deprecated_pydantic_schema_plugin_imports() -> None:
    purge_module(["litestar.contrib.pydantic.pydantic_schema_plugin"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PydanticSchemaPlugin from 'litestar.contrib.pydantic' is deprecated",
    ):
        from litestar.contrib.pydantic import PydanticSchemaPlugin


def test_deprecated_pydantic_di_plugin_imports() -> None:
    purge_module(["litestar.contrib.pydantic"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing PydanticDIPlugin from 'litestar.contrib.pydantic' is deprecated",
    ):
        from litestar.contrib.pydantic import PydanticDIPlugin


def test_deprecated_pydantic_utils_imports() -> None:
    purge_module(["litestar.contrib.pydantic.utils"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing get_model_info from 'litestar.contrib.pydantic.utils' is deprecated",
    ):
        from litestar.contrib.pydantic.utils import get_model_info

    purge_module(["litestar.contrib.pydantic.utils"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing is_pydantic_constrained_field from 'litestar.contrib.pydantic.utils' is deprecated",
    ):
        from litestar.contrib.pydantic.utils import is_pydantic_constrained_field

    purge_module(["litestar.contrib.pydantic.utils"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing is_pydantic_model_class from 'litestar.contrib.pydantic.utils' is deprecated",
    ):
        from litestar.contrib.pydantic.utils import is_pydantic_model_class

    purge_module(["litestar.contrib.pydantic.utils"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing is_pydantic_undefined from 'litestar.contrib.pydantic.utils' is deprecated",
    ):
        from litestar.contrib.pydantic.utils import is_pydantic_undefined

    purge_module(["litestar.contrib.pydantic.utils"], __file__)
    with pytest.warns(
        DeprecationWarning,
        match="importing is_pydantic_v2 from 'litestar.contrib.pydantic.utils' is deprecated",
    ):
        from litestar.contrib.pydantic.utils import is_pydantic_v2
