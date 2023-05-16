from __future__ import annotations

from asyncio import AbstractEventLoop, get_event_loop_policy
from datetime import datetime
from typing import TYPE_CHECKING, Any, Iterator
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.sqlalchemy_aiosqlite
@pytest.fixture(scope="session")
def event_loop() -> Iterator[AbstractEventLoop]:
    """Need the event loop scoped to the session so that we can use it to check
    containers are ready in session scoped containers fixture."""
    policy = get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def _patch_bases(monkeypatch: MonkeyPatch) -> None:
    """Ensure new registry state for every test.

    This prevents errors such as "Table '...' is already defined for
    this MetaData instance...
    """
    from sqlalchemy.orm import DeclarativeBase

    from litestar.contrib.sqlalchemy import base

    class NewUUIDBase(base.UUIDPrimaryKey, base.CommonTableAttributes, DeclarativeBase):
        ...

    class NewUUIDAuditBase(base.UUIDPrimaryKey, base.CommonTableAttributes, base.AuditColumns, DeclarativeBase):
        ...

    class NewBigIntBase(base.BigIntPrimaryKey, base.CommonTableAttributes, DeclarativeBase):
        ...

    class NewBigIntAuditBase(base.BigIntPrimaryKey, base.CommonTableAttributes, base.AuditColumns, DeclarativeBase):
        ...

    monkeypatch.setattr(base, "UUIDBase", NewUUIDBase)
    monkeypatch.setattr(base, "UUIDAuditBase", NewUUIDAuditBase)
    monkeypatch.setattr(base, "BigIntBase", NewBigIntBase)
    monkeypatch.setattr(base, "BigIntAuditBase", NewBigIntAuditBase)


@pytest.fixture(name="raw_authors")
def fx_raw_authors() -> list[dict[str, Any]]:
    """Unstructured author representations."""
    return [
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
        {
            "id": "5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2",
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_books")
def fx_raw_books(raw_authors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unstructured book representations."""
    return [
        {
            "id": UUID("f34545b9-663c-4fce-915d-dd1ae9cea42a"),
            "title": "Murder on the Orient Express",
            "author_id": "97108ac1-ffcb-411d-8b1e-d9183399f63b",
            "author": raw_authors[0],
        },
    ]


@pytest.fixture(name="raw_log_events")
def fx_raw_log_events() -> list[dict[str, Any]]:
    """Unstructured log events representations."""
    return [
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea42a",
            "logged_at": "0001-01-01T00:00:00",
            "payload": {"foo": "bar", "baz": datetime.now()},
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_ingredients")
def fx_raw_ingredients() -> list[dict[str, Any]]:
    """Unstructured ingredients representations."""
    return [{"name": "Apple"}, {"name": "Orange"}]


@pytest.fixture(name="raw_stores")
def fx_raw_stores() -> list[dict[str, Any]]:
    """Unstructured store representations."""
    return [
        {
            "store_name": "Super Market - Talladega, AL",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
        {
            "store_name": "Corner Store - Moody, AL",
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]
