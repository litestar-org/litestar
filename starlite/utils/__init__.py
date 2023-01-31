from starlite.utils.deprecation import deprecated, warn_deprecation

from .csrf import generate_csrf_hash, generate_csrf_token
from .exception import (
    ExceptionResponseContent,
    create_exception_response,
    get_exception_handler,
)
from .extractors import ConnectionDataExtractor, ResponseDataExtractor, obfuscate
from .helpers import Ref, get_enum_string_value, get_name
from .model import (
    convert_dataclass_to_model,
    convert_typeddict_to_model,
    create_parsed_model_field,
)
from .path import join_paths, normalize_path
from .predicates import (
    is_any,
    is_class_and_subclass,
    is_dataclass_class,
    is_dataclass_class_or_instance,
    is_mapping,
    is_optional_union,
    is_typed_dict,
    is_union,
)
from .scope import (
    get_serializer_from_scope,
    get_starlite_scope_state,
    set_starlite_scope_state,
)
from .sequence import find_index, unique
from .serialization import (
    decode_json,
    decode_msgpack,
    default_serializer,
    encode_json,
    encode_msgpack,
)
from .sync import (
    AsyncCallable,
    AsyncIteratorWrapper,
    as_async_callable_list,
    async_partial,
    is_async_callable,
)
from .types import annotation_is_iterable_of_type, make_non_optional_union

__all__ = (
    "AsyncCallable",
    "AsyncIteratorWrapper",
    "ConnectionDataExtractor",
    "ExceptionResponseContent",
    "Ref",
    "ResponseDataExtractor",
    "annotation_is_iterable_of_type",
    "as_async_callable_list",
    "async_partial",
    "convert_dataclass_to_model",
    "convert_typeddict_to_model",
    "create_exception_response",
    "create_parsed_model_field",
    "decode_json",
    "decode_msgpack",
    "default_serializer",
    "deprecated",
    "encode_json",
    "encode_msgpack",
    "find_index",
    "generate_csrf_hash",
    "generate_csrf_token",
    "get_enum_string_value",
    "get_exception_handler",
    "get_name",
    "get_serializer_from_scope",
    "get_starlite_scope_state",
    "is_any",
    "is_async_callable",
    "is_class_and_subclass",
    "is_dataclass_class",
    "is_dataclass_class_or_instance",
    "is_optional_union",
    "is_typed_dict",
    "is_union",
    "is_mapping",
    "join_paths",
    "make_non_optional_union",
    "normalize_path",
    "obfuscate",
    "set_starlite_scope_state",
    "unique",
    "warn_deprecation",
)
