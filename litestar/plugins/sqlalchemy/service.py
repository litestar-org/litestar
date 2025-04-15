from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

# Symbols defined in advanced_alchemy.service.__all__
_EXPORTED_SYMBOLS = {
    "DEFAULT_ERROR_MESSAGE_TEMPLATES",
    "Empty",
    "EmptyType",
    "ErrorMessages",
    "FilterTypeT",  # TypeVar
    "LoadSpec",
    "ModelDTOT",  # TypeVar
    "ModelDictListT",  # TypeAlias
    "ModelDictT",  # TypeAlias
    "ModelOrRowMappingT",  # TypeAlias
    "ModelT",  # TypeVar
    "OffsetPagination",
    "OrderingPair",  # TypeAlias
    "ResultConverter",
    "SQLAlchemyAsyncQueryService",
    "SQLAlchemyAsyncRepositoryReadService",
    "SQLAlchemyAsyncRepositoryService",
    "SQLAlchemySyncQueryService",
    "SQLAlchemySyncRepositoryReadService",
    "SQLAlchemySyncRepositoryService",
    "SupportedSchemaModel",  # Protocol
    "find_filter",
    "is_dict",
    "is_dict_with_field",
    "is_dict_without_field",
    "is_dto_data",
    "is_msgspec_struct",
    "is_msgspec_struct_with_field",
    "is_msgspec_struct_without_field",
    "is_pydantic_model",
    "is_pydantic_model_with_field",
    "is_pydantic_model_without_field",
    "is_schema",
    "is_schema_or_dict",
    "is_schema_or_dict_with_field",
    "is_schema_or_dict_without_field",
    "is_schema_with_field",
    "is_schema_without_field",
    "model_from_dict",
    "schema_dump",
}

_SOURCE_MODULE = "advanced_alchemy.service"


def __getattr__(name: str) -> Any:
    """Load symbols lazily from the underlying Advanced Alchemy module."""
    if name in _EXPORTED_SYMBOLS:
        module = importlib.import_module(_SOURCE_MODULE)
        attr = getattr(module, name)
        # Cache it in the current module's globals
        globals()[name] = attr
        return attr

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Define __all__ statically based on the symbols being lazy-loaded
# Excluding TypeVars/Aliases/Protocols from runtime __all__
__all__ = (
    "DEFAULT_ERROR_MESSAGE_TEMPLATES",
    "Empty",
    "EmptyType",
    "ErrorMessages",
    "FilterTypeT",
    "LoadSpec",
    "ModelDTOT",
    "ModelDictListT",
    "ModelDictT",
    "ModelOrRowMappingT",
    "ModelT",
    "OffsetPagination",
    "OrderingPair",
    "ResultConverter",
    "SQLAlchemyAsyncQueryService",
    "SQLAlchemyAsyncRepositoryReadService",
    "SQLAlchemyAsyncRepositoryService",
    "SQLAlchemySyncQueryService",
    "SQLAlchemySyncRepositoryReadService",
    "SQLAlchemySyncRepositoryService",
    "SupportedSchemaModel",
    "find_filter",
    "is_dict",
    "is_dict_with_field",
    "is_dict_without_field",
    "is_dto_data",
    "is_msgspec_struct",
    "is_msgspec_struct_with_field",
    "is_msgspec_struct_without_field",
    "is_pydantic_model",
    "is_pydantic_model_with_field",
    "is_pydantic_model_without_field",
    "is_schema",
    "is_schema_or_dict",
    "is_schema_or_dict_with_field",
    "is_schema_or_dict_without_field",
    "is_schema_with_field",
    "is_schema_without_field",
    "model_from_dict",
    "schema_dump",
)

if TYPE_CHECKING:
    from advanced_alchemy.service import (
        DEFAULT_ERROR_MESSAGE_TEMPLATES,
        Empty,
        EmptyType,
        ErrorMessages,
        FilterTypeT,
        LoadSpec,
        ModelDictListT,
        ModelDictT,
        ModelDTOT,
        ModelOrRowMappingT,
        ModelT,
        OffsetPagination,
        OrderingPair,
        ResultConverter,
        SQLAlchemyAsyncQueryService,
        SQLAlchemyAsyncRepositoryReadService,
        SQLAlchemyAsyncRepositoryService,
        SQLAlchemySyncQueryService,
        SQLAlchemySyncRepositoryReadService,
        SQLAlchemySyncRepositoryService,
        SupportedSchemaModel,
        find_filter,
        is_dict,
        is_dict_with_field,
        is_dict_without_field,
        is_dto_data,
        is_msgspec_struct,
        is_msgspec_struct_with_field,
        is_msgspec_struct_without_field,
        is_pydantic_model,
        is_pydantic_model_with_field,
        is_pydantic_model_without_field,
        is_schema,
        is_schema_or_dict,
        is_schema_or_dict_with_field,
        is_schema_or_dict_without_field,
        is_schema_with_field,
        is_schema_without_field,
        model_from_dict,
        schema_dump,
    )
