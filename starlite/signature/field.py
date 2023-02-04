from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

from pydantic.fields import ModelField
from typing_extensions import get_args, get_origin

from starlite.constants import UNDEFINED_SENTINELS
from starlite.params import BodyKwarg, DependencyKwarg, ParameterKwarg
from starlite.types import Empty
from starlite.utils import (
    is_any,
    is_mapping,
    is_optional_union,
    is_union,
    make_non_optional_union,
)
from starlite.utils.predicates import (
    is_generic,
    is_non_string_iterable,
    is_non_string_sequence,
)


@dataclass(unsafe_hash=True, frozen=True)
class SignatureField:
    """Abstraction representing a model field. This class is meant to replace equivalent datastructures from, other
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

    children: Optional[Tuple["SignatureField", ...]]
    """A mapping of subtypes, if any."""
    default_value: Any
    """Field name."""
    extra: Dict[str, Any]
    """A mapping of extra values."""
    field_type: Any
    """The type of the kwarg."""
    kwarg_model: Optional[Union["ParameterKwarg", "BodyKwarg", "DependencyKwarg"]]
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

        See: https://github.com/starlite-api/starlite/issues/1106
        """
        field_type = self.field_type
        if self.is_optional:
            field_type = make_non_optional_union(field_type)
        return is_non_string_iterable(field_type)

    @property
    def is_non_string_sequence(self) -> bool:
        """Check if the field type is a non-string Sequence.

        If ``self.field_type`` is an optional union, only the non-optional members of the union are evaluated.

        See: https://github.com/starlite-api/starlite/issues/1106
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

    @classmethod
    def create(
        cls,
        field_type: Any,
        name: str = "",
        default_value: Any = Empty,
        children: Optional[Tuple["SignatureField", ...]] = None,
        kwarg_model: Optional[Union[ParameterKwarg, BodyKwarg, DependencyKwarg]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> "SignatureField":
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

    @classmethod
    def from_model_field(cls, model_field: ModelField) -> "SignatureField":
        """Create a SignatureField instance from a pydantic ModelField.

        Args:
            model_field: A pydantic ModelField instance.

        Returns:
            A SignatureField
        """
        children = (
            tuple(cls.from_model_field(sub_field) for sub_field in model_field.sub_fields)
            if model_field.sub_fields
            else None
        )
        default_value = (
            model_field.field_info.default if model_field.field_info.default not in UNDEFINED_SENTINELS else Empty
        )

        kwarg_model: Optional[Union[ParameterKwarg, DependencyKwarg, BodyKwarg]] = model_field.field_info.extra.pop(
            "kwargs_model", None
        )
        if kwarg_model:
            default_value = kwarg_model.default
        elif isinstance(default_value, (ParameterKwarg, DependencyKwarg, BodyKwarg)):
            kwarg_model = default_value
            default_value = default_value.default

        return SignatureField(
            children=children,
            default_value=default_value,
            extra=model_field.field_info.extra or {},
            field_type=model_field.annotation if model_field.annotation is not Empty else Any,
            kwarg_model=kwarg_model,
            name=model_field.name,
        )
