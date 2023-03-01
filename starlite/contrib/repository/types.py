"""Repository type definitions."""
from __future__ import annotations

from typing import Any

from starlite.contrib.repository.filters import (
    BeforeAfter,
    CollectionFilter,
    LimitOffset,
)

FilterTypes = BeforeAfter | CollectionFilter[Any] | LimitOffset
"""Aggregate type alias of the types supported for collection filtering."""
