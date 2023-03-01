"""Repository type definitions."""
from __future__ import annotations

from typing import Any, Union

from starlite.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    LimitOffset,
)

FilterTypes = Union[BeforeAfter, CollectionFilter[Any], LimitOffset]
"""Aggregate type alias of the types supported for collection filtering."""
