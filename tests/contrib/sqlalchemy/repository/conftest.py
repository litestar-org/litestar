from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.fixture(autouse=True)
def _patch_bases(monkeypatch: MonkeyPatch) -> None:
    """Ensure new registry state for every test.

    This prevents errors such as "Table '...' is already defined for
    this MetaData instance...
    """
    from sqlalchemy.orm import DeclarativeBase

    from litestar.contrib.sqlalchemy import base

    class NewBase(base.UUIDPrimaryKey, base.CommonTableAttributes, DeclarativeBase):
        ...

    class NewAuditBase(base.UUIDPrimaryKey, base.CommonTableAttributes, base.AuditColumns, DeclarativeBase):
        ...

    monkeypatch.setattr(base, "Base", NewBase)
    monkeypatch.setattr(base, "AuditBase", NewAuditBase)
