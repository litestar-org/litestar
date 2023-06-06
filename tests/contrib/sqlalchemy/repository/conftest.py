from __future__ import annotations

import json
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


@pytest.fixture(name="raw_authors_uuid")
def fx_raw_authors_uuid() -> list[dict[str, Any]]:
    """Unstructured author representations."""
    return [
        {
            "id": UUID("97108ac1-ffcb-411d-8b1e-d9183399f63b"),
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created": "2023-05-01T00:00:00",
            "updated": "2023-05-11T00:00:00",
        },
        {
            "id": "5ef29f3c-3560-4d15-ba6b-a2e5c721e4d2",
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created": "2023-03-01T00:00:00",
            "updated": "2023-05-15T00:00:00",
        },
    ]


@pytest.fixture(name="raw_books_uuid")
def fx_raw_books_uuid(raw_authors_uuid: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unstructured book representations."""
    return [
        {
            "id": UUID("f34545b9-663c-4fce-915d-dd1ae9cea42a"),
            "title": "Murder on the Orient Express",
            "author_id": raw_authors_uuid[0]["id"],
            "author": raw_authors_uuid[0],
        },
    ]


@pytest.fixture(name="raw_log_events_uuid")
def fx_raw_log_events_uuid() -> list[dict[str, Any]]:
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


@pytest.fixture(name="raw_rules_uuid")
def fx_raw_rules_uuid() -> list[dict[str, Any]]:
    """Unstructured rules representations."""
    return [
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea42a",
            "name": "Initial loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "setting_123": 1}),
            "created": "2023-01-01T00:00:00",
            "updated": "2023-02-01T00:00:00",
        },
        {
            "id": "f34545b9-663c-4fce-915d-dd1ae9cea34b",
            "name": "Secondary loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "bar": "foo", "setting_123": 4}),
            "created": "2023-02-01T00:00:00",
            "updated": "2023-02-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_authors_bigint")
def fx_raw_authors_bigint() -> list[dict[str, Any]]:
    """Unstructured author representations."""
    return [
        {
            "id": 2023,
            "name": "Agatha Christie",
            "dob": "1890-09-15",
            "created": "2023-05-01T00:00:00",
            "updated": "2023-05-11T00:00:00",
        },
        {
            "id": 2024,
            "name": "Leo Tolstoy",
            "dob": "1828-09-09",
            "created": "2023-03-01T00:00:00",
            "updated": "2023-05-15T00:00:00",
        },
    ]


@pytest.fixture(name="raw_books_bigint")
def fx_raw_books_bigint(raw_authors_bigint: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Unstructured book representations."""
    return [
        {
            "title": "Murder on the Orient Express",
            "author_id": raw_authors_bigint[0]["id"],
            "author": raw_authors_bigint[0],
        },
    ]


@pytest.fixture(name="raw_log_events_bigint")
def fx_raw_log_events_bigint() -> list[dict[str, Any]]:
    """Unstructured log events representations."""
    return [
        {
            "id": 2025,
            "logged_at": "0001-01-01T00:00:00",
            "payload": {"foo": "bar", "baz": datetime.now()},
            "created": "0001-01-01T00:00:00",
            "updated": "0001-01-01T00:00:00",
        },
    ]


@pytest.fixture(name="raw_rules_bigint")
def fx_raw_rules_bigint() -> list[dict[str, Any]]:
    """Unstructured rules representations."""
    return [
        {
            "id": 2025,
            "name": "Initial loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "setting_123": 1}),
            "created": "2023-01-01T00:00:00",
            "updated": "2023-02-01T00:00:00",
        },
        {
            "id": 2024,
            "name": "Secondary loading rule.",
            "config": json.dumps({"url": "https://litestar.dev", "bar": "foo", "setting_123": 4}),
            "created": "2023-02-01T00:00:00",
            "updated": "2023-02-01T00:00:00",
        },
    ]
