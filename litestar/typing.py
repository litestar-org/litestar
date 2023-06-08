from __future__ import annotations

from collections import abc
from dataclasses import dataclass
from typing import Any, AnyStr, Collection, ForwardRef, Mapping, TypeVar

from typing_extensions import Annotated, NotRequired, Required, get_args, get_origin

from litestar.types.builtin_types import UNION_TYPES, NoneType
from litestar.utils.typing import get_instantiable_origin, get_safe_generic_origin, unwrap_annotation

__all__ = ("ParsedType",)


@dataclass(frozen=True, init=False)
class ParsedType:
    """Represents a type annotation."""

    __slots__ = (
        "raw",
        "annotation",
        "origin",
        "args",
        "metadata",
        "instantiable_origin",
        "is_annotated",
        "is_required",
        "is_not_required",
        "safe_generic_origin",
        "inner_types",
    )

    raw: Any
    """The annotation exactly as received."""
    annotation: Any
    """The annotation with any "wrapper" types removed, e.g. Annotated."""
    origin: Any
    """The result of calling ``get_origin(annotation)`` after unwrapping Annotated, e.g. list."""
    args: tuple[Any, ...]
    """The result of calling ``get_args(annotation)`` after unwrapping Annotated, e.g. (int,)."""
    metadata: tuple[Any, ...]
    """Any metadata associated with the annotation via ``Annotated``."""
    instantiable_origin: Any
    """An equivalent type to ``origin`` that can be safely instantiated. E.g., ``Sequence`` -> ``list``."""
    is_annotated: bool
    """Whether the annotation included ``Annotated`` or not."""
    is_required: bool
    """Whether the annotation included ``Required`` or not."""
    is_not_required: bool
    """Whether the annotation included ``NotRequired`` or not."""
    safe_generic_origin: Any
    """An equivalent type to ``origin`` that can be safely used as a generic type across all supported Python versions.

    This is to serve safely rebuilding a generic outer type with different args at runtime.
    """
    inner_types: tuple[ParsedType, ...]
    """The type's generic args parsed as ``ParsedType``, if applicable."""

    def __init__(self, annotation: Any) -> None:
        """Initialize ParsedType.

        Args:
            annotation: The type annotation. This should be extracted from the return of
                ``get_type_hints(..., include_extras=True)`` so that forward references are resolved and recursive
                ``Annotated`` types are flattened.

        Returns:
            ParsedType
        """
        unwrapped, metadata, wrappers = unwrap_annotation(annotation)
        origin = get_origin(unwrapped)

        args = () if origin is abc.Callable else get_args(unwrapped)

        object.__setattr__(self, "raw", annotation)
        object.__setattr__(self, "annotation", unwrapped)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "instantiable_origin", get_instantiable_origin(origin, unwrapped))
        object.__setattr__(self, "is_annotated", Annotated in wrappers)
        object.__setattr__(self, "is_required", Required in wrappers)
        object.__setattr__(self, "is_not_required", NotRequired in wrappers)
        object.__setattr__(self, "safe_generic_origin", get_safe_generic_origin(origin, unwrapped))
        object.__setattr__(self, "inner_types", tuple(ParsedType(arg) for arg in args))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ParsedType):
            return False

        if self.origin:
            return bool(self.origin == other.origin and self.inner_types == other.inner_types)

        return bool(self.annotation == other.annotation)

    @property
    def is_forward_ref(self) -> bool:
        """Whether the annotation is a forward reference or not."""
        return isinstance(self.annotation, (str, ForwardRef))

    @property
    def is_mapping(self) -> bool:
        """Whether the annotation is a mapping or not."""
        return self.is_subclass_of(Mapping)

    @property
    def is_tuple(self) -> bool:
        """Whether the annotation is a ``tuple`` or not."""
        return self.is_subclass_of(tuple)

    @property
    def is_type_var(self) -> bool:
        """Whether the annotation is a TypeVar or not."""
        return isinstance(self.annotation, TypeVar)

    @property
    def is_union(self) -> bool:
        """Whether the annotation is a union type or not."""
        return self.origin in UNION_TYPES

    @property
    def is_optional(self) -> bool:
        """Whether the annotation is Optional or not."""
        return bool(self.is_union and NoneType in self.args)

    @property
    def is_collection(self) -> bool:
        """Whether the annotation is a collection type or not."""
        return self.is_subclass_of(Collection)

    @property
    def is_non_string_collection(self) -> bool:
        """Whether the annotation is a non-string collection type or not."""
        return self.is_collection and not self.is_subclass_of((str, bytes))

    def is_subclass_of(self, cl: type[Any] | tuple[type[Any], ...]) -> bool:
        """Whether the annotation is a subclass of the given type.

        Where ``self.annotation`` is a union type, this method will return ``True`` when all members of the union are
        a subtype of ``cl``, otherwise, ``False``.

        Args:
            cl: The type to check, or tuple of types. Passed as 2nd argument to ``issubclass()``.

        Returns:
            Whether the annotation is a subtype of the given type(s).
        """
        if self.origin:
            if self.origin in UNION_TYPES:
                return all(t.is_subclass_of(cl) for t in self.inner_types)

            return self.origin not in UNION_TYPES and issubclass(self.origin, cl)

        if self.annotation is AnyStr:
            return issubclass(str, cl) or issubclass(bytes, cl)
        return self.annotation is not Any and not self.is_type_var and issubclass(self.annotation, cl)

    def has_inner_subclass_of(self, cl: type[Any] | tuple[type[Any], ...]) -> bool:
        """Whether any generic args are a subclass of the given type.

        Args:
            cl: The type to check, or tuple of types. Passed as 2nd argument to ``issubclass()``.

        Returns:
            Whether any of the type's generic args are a subclass of the given type.
        """
        return any(t.is_subclass_of(cl) for t in self.inner_types)
