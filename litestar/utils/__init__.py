from litestar.utils.deprecation import deprecated, warn_deprecation

from .helpers import Ref, get_enum_string_value, get_name
from .path import join_paths, normalize_path
from .predicates import (
    is_any,
    is_attrs_class,
    is_class_and_subclass,
    is_class_var,
    is_dataclass_class,
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
    is_optional_union,
    is_pydantic_constrained_field,
    is_pydantic_model_class,
    is_pydantic_model_instance,
    is_typed_dict,
    is_union,
)
from .scope import (
    delete_litestar_scope_state,
    get_litestar_scope_state,
    get_serializer_from_scope,
    set_litestar_scope_state,
)
from .sequence import compact, find_index, unique
from .sync import (
    AsyncCallable,
    AsyncIteratorWrapper,
    as_async_callable_list,
    async_partial,
    is_async_callable,
)
from .typing import annotation_is_iterable_of_type, get_origin_or_inner_type, make_non_optional_union

__all__ = (
    "AsyncCallable",
    "AsyncIteratorWrapper",
    "Ref",
    "annotation_is_iterable_of_type",
    "as_async_callable_list",
    "async_partial",
    "compact",
    "delete_litestar_scope_state",
    "deprecated",
    "find_index",
    "get_enum_string_value",
    "get_litestar_scope_state",
    "get_name",
    "get_origin_or_inner_type",
    "get_serializer_from_scope",
    "is_any",
    "is_async_callable",
    "is_attrs_class",
    "is_class_and_subclass",
    "is_class_var",
    "is_dataclass_class",
    "is_generic",
    "is_mapping",
    "is_non_string_iterable",
    "is_non_string_sequence",
    "is_optional_union",
    "is_pydantic_constrained_field",
    "is_pydantic_model_class",
    "is_pydantic_model_instance",
    "is_typed_dict",
    "is_union",
    "join_paths",
    "make_non_optional_union",
    "normalize_path",
    "set_litestar_scope_state",
    "unique",
    "warn_deprecation",
)
