from litestar.utils.deprecation import deprecated, warn_deprecation

from .helpers import get_enum_string_value, get_name, unique_name_for_scope, url_quote
from .path import join_paths, normalize_path
from .predicates import (
    is_annotated_type,
    is_any,
    is_async_callable,
    is_attrs_class,
    is_class_and_subclass,
    is_class_var,
    is_dataclass_class,
    is_dataclass_instance,
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
    is_optional_union,
    is_sync_or_async_generator,
    is_undefined_sentinel,
    is_union,
)
from .scope import (
    delete_litestar_scope_state,
    get_litestar_scope_state,
    get_serializer_from_scope,
    set_litestar_scope_state,
)
from .sequence import find_index, unique
from .sync import AsyncIteratorWrapper, ensure_async_callable
from .typing import get_origin_or_inner_type, make_non_optional_union

__all__ = (
    "ensure_async_callable",
    "AsyncIteratorWrapper",
    "delete_litestar_scope_state",
    "deprecated",
    "find_index",
    "get_enum_string_value",
    "get_litestar_scope_state",
    "get_name",
    "get_origin_or_inner_type",
    "get_serializer_from_scope",
    "is_annotated_type",
    "is_any",
    "is_async_callable",
    "is_attrs_class",
    "is_class_and_subclass",
    "is_class_var",
    "is_dataclass_class",
    "is_dataclass_instance",
    "is_generic",
    "is_mapping",
    "is_non_string_iterable",
    "is_non_string_sequence",
    "is_optional_union",
    "is_sync_or_async_generator",
    "is_undefined_sentinel",
    "is_union",
    "join_paths",
    "make_non_optional_union",
    "normalize_path",
    "set_litestar_scope_state",
    "unique",
    "unique_name_for_scope",
    "url_quote",
    "warn_deprecation",
)
