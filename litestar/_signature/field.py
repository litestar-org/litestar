from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from typing_extensions import get_args, get_origin

from litestar.constants import UNDEFINED_SENTINELS
from litestar.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from litestar.types import Empty
from litestar.utils.predicates import (
    is_any,
    is_generic,
    is_mapping,
    is_non_string_iterable,
    is_non_string_sequence,
    is_optional_union,
    is_union,
)
from litestar.utils.typing import make_non_optional_union

__all__ = ("SignatureField",)


@dataclass(unsafe_hash=True, frozen=True)
class SignatureField:
    """Abstraction representing a model field. This class is meant to replace equivalent datastructures from other
    libraries, for example, pydantic or msgspec.
    """

    __slots__ = (
        "children",
        "default_value",
        "extra",
        "field_type",
        "kwarg_model",
        "name",
    )

    children: tuple[SignatureField, ...] | None
    """A mapping of subtypes, if any."""
    default_value: Any
    """Field name."""
    extra: dict[str, Any]
    """A mapping of extra values."""
    field_type: Any
    """The type of the kwarg."""
    kwarg_model: ParameterKwarg | BodyKwarg | DependencyKwarg | None
    """Kwarg Parameter."""
    name: str
    """Field name."""

    @property
    def is_empty(self) -> bool:
        """Check if the default value is an empty type.

        Returns:
            True if the default_value is Empty or Ellipsis otherwise False.
        """
        return self.default_value is Empty or self.default_value is Ellipsis

    @property
    def is_optional(self) -> bool:
        """Check if the field type is an Optional union.

        Returns:
            True if the field_type is an Optional union otherwise False.
        """
        return is_optional_union(self.field_type)

    @property
    def is_mapping(self) -> bool:
        """Check if the field type is a Mapping."""
        return is_mapping(self.field_type)

    @property
    def is_non_string_iterable(self) -> bool:
        """Check if the field type is an Iterable.

        If ``self.field_type`` is an optional union, only the non-optional members of the union are evaluated.

        See: https://github.com/litestar-org/litestar/issues/1106
        """
        field_type = self.field_type
        if self.is_optional:
            field_type = make_non_optional_union(field_type)
        return is_non_string_iterable(field_type)

    @property
    def is_non_string_sequence(self) -> bool:
        """Check if the field type is a non-string Sequence.

        If ``self.field_type`` is an optional union, only the non-optional members of the union are evaluated.

        See: https://github.com/litestar-org/litestar/issues/1106
        """
        field_type = self.field_type
        if self.is_optional:
            field_type = make_non_optional_union(field_type)
        return is_non_string_sequence(field_type)

    @property
    def is_any(self) -> bool:
        """Check if the field type is Any."""
        return is_any(self.field_type)

    @property
    def is_union(self) -> bool:
        """Check if the field type is a Union."""
        return is_union(self.field_type)

    @property
    def is_generic(self) -> bool:
        """Check if the field type is a custom class extending Generic."""
        return is_generic(self.field_type)

    @property
    def is_simple_type(self) -> bool:
        """Check if the field type is a singleton value (e.g. int, str etc.)."""
        return not (
            self.is_generic or self.is_optional or self.is_union or self.is_mapping or self.is_non_string_iterable
        )

    @property
    def is_parameter_field(self) -> bool:
        """Check if the field type is a parameter kwarg value."""
        return self.kwarg_model is not None and isinstance(self.kwarg_model, ParameterKwarg)

    @property
    def is_const(self) -> bool:
        """Check if the field is defined as constant value."""
        return bool(self.kwarg_model and getattr(self.kwarg_model, "const", False))

    @property
    def is_required(self) -> bool:
        """Check if the field should be marked as a required parameter."""
        if isinstance(self.kwarg_model, ParameterKwarg) and self.kwarg_model.required is not None:
            return self.kwarg_model.required

        return not (self.is_optional or self.is_any) and (self.is_empty or self.default_value is None)

    @property
    def is_literal(self) -> bool:
        """Check if the field type is Literal."""
        return get_origin(self.field_type) is Literal

    @classmethod
    def create(
        cls,
        field_type: Any,
        name: str = "",
        default_value: Any = Empty,
        children: tuple[SignatureField, ...] | None = None,
        kwarg_model: ParameterKwarg | BodyKwarg | DependencyKwarg | None = None,
        extra: dict[str, Any] | None = None,
    ) -> SignatureField:
        """Create a new SignatureModel instance.

        Args:
            field_type: The type of the kwarg.
            name: Field name.
            default_value: A default value.
            children: A mapping of subtypes, if any.
            kwarg_model: Kwarg Parameter.
            extra: A mapping of extra values.

        Returns:
            SignatureField instance.
        """
        if kwarg_model and default_value is Empty:
            default_value = kwarg_model.default

        if not children and get_origin(field_type) and (type_args := get_args(field_type)):
            children = tuple(SignatureField.create(arg) for arg in type_args)

        return SignatureField(
            name=name,
            field_type=field_type if field_type is not Empty else Any,
            default_value=default_value if default_value not in UNDEFINED_SENTINELS else Empty,
            children=children,
            kwarg_model=kwarg_model,
            extra=extra or {},
        )
