from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any, Awaitable, TypeVar, cast, overload

T = TypeVar("T")


@overload
async def maybe_async(obj: Awaitable[T]) -> T:
    ...


@overload
async def maybe_async(obj: T) -> T:
    ...


async def maybe_async(obj: Awaitable[T] | T) -> T:
    if inspect.isawaitable(obj):
        return cast(T, await obj)
    return cast(T, obj)


def update_raw_records(raw_authors: list[dict[str, Any]], raw_rules: list[dict[str, Any]]) -> None:
    for raw_author in raw_authors:
        raw_author["dob"] = datetime.strptime(raw_author["dob"], "%Y-%m-%d").date()
        raw_author["created"] = datetime.strptime(raw_author["created"], "%Y-%m-%dT%H:%M:%S")
        raw_author["updated"] = datetime.strptime(raw_author["updated"], "%Y-%m-%dT%H:%M:%S")
    for raw_rule in raw_rules:
        raw_rule["created"] = datetime.strptime(raw_rule["created"], "%Y-%m-%dT%H:%M:%S")
        raw_rule["updated"] = datetime.strptime(raw_rule["updated"], "%Y-%m-%dT%H:%M:%S")
