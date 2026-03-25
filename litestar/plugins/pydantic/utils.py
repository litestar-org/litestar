# mypy: strict-equality=False
# pyright: reportGeneralTypeIssues=false
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Literal, NotRequired, get_type_hints

import pydantic
from pydantic_core import PydanticUndefined

from litestar.openapi.spec import Example
from litestar.params import KwargDefinition, ParameterKwarg
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils import is_class_and_subclass, is_generic, is_undefined_sentinel
from litestar.utils.typing import (
    _substitute_typevars,
    normalize_type_annotation,
)

if TYPE_CHECKING:
    from types import ModuleType
    from typing import TypeGuard


def is_pydantic_model_class(
    annotation: Any,
) -> TypeGuard[type[pydantic.BaseModel]]:  # pyright: ignore
    """Given a type annotation determine if the annotation is a subclass of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    return is_class_and_subclass(annotation, pydantic.BaseModel)


def is_pydantic_model_instance(
    annotation: Any,
) -> TypeGuard[pydantic.BaseModel]:  # pyright: ignore
    """Given a type annotation determine if the annotation is an instance of pydantic's BaseModel.

    Args:
        annotation: A type.

    Returns:
        A typeguard determining whether the type is :data:`BaseModel pydantic.BaseModel>`.
    """
    return isinstance(annotation, pydantic.BaseModel)


def pydantic_unwrap_and_get_origin(annotation: Any) -> Any | None:
    origin = annotation.__pydantic_generic_metadata__["origin"]
    return normalize_type_annotation(origin)


def pydantic_get_type_hints_with_generics_resolved(
    annotation: Any,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
    include_extras: bool = False,
    model_annotations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    origin = pydantic_unwrap_and_get_origin(annotation)
    if origin is None:
        if model_annotations is None:  # pragma: no cover
            model_annotations = get_type_hints(
                annotation, globalns=globalns, localns=localns, include_extras=include_extras
            )
        typevar_map = {p: p for p in annotation.__pydantic_generic_metadata__["parameters"]}
    else:
        if model_annotations is None:
            model_annotations = get_type_hints(
                origin, globalns=globalns, localns=localns, include_extras=include_extras
            )
        args = annotation.__pydantic_generic_metadata__["args"]
        parameters = origin.__pydantic_generic_metadata__["parameters"]
        typevar_map = dict(zip(parameters, args, strict=False))

    return {n: _substitute_typevars(type_, typevar_map) for n, type_ in model_annotations.items()}


def is_pydantic_2_model(
    obj: type[pydantic.BaseModel],  # pyright: ignore
) -> TypeGuard[pydantic.BaseModel]:  # pyright: ignore
    return issubclass(obj, pydantic.BaseModel)


def is_pydantic_undefined(value: Any) -> bool:
    return value is PydanticUndefined


def create_field_definitions_for_computed_fields(
    model: type[pydantic.BaseModel],  # pyright: ignore
    prefer_alias: bool,
) -> dict[str, FieldDefinition]:
    """Create field definitions for computed fields.

    Args:
        model: A pydantic model.
        prefer_alias: Whether to prefer the alias or the name of the field.

    Returns:
        A dictionary containing the field definitions for the computed fields.
    """
    pydantic_decorators = getattr(model, "__pydantic_decorators__", None)
    if pydantic_decorators is None:
        return {}

    def get_name(k: str, dec: Any) -> str:
        if not dec.info.alias:
            return k
        return dec.info.alias if prefer_alias else k  # type: ignore[no-any-return]

    return {
        (name := get_name(k, dec)): FieldDefinition.from_annotation(
            Annotated[
                dec.info.return_type,
                KwargDefinition(
                    title=dec.info.title,
                    description=dec.info.description,
                    read_only=True,
                    examples=[Example(value=v) for v in examples] if (examples := dec.info.examples) else None,
                    schema_extra=dec.info.json_schema_extra,
                ),
            ],
            name=name,
        )
        for k, dec in pydantic_decorators.computed_fields.items()
    }


def is_pydantic_v2(module: ModuleType) -> bool:
    """Determine if the given module is pydantic v2.

    Given a module we expect to be a pydantic version, determine if it is pydantic v2.

    Args:
        module: A module.

    Returns:
        True if the module is pydantic v2, otherwise False.
    """
    return bool(module.__version__.startswith("2."))


def is_pydantic_root_model(annotation: Any) -> bool:
    """Check if the given annotation is a Pydantic RootModel.

    Args:
        annotation: A type annotation

    Returns:
        True if the annotation is a RootModel, otherwise False.
    """
    return getattr(annotation, "__pydantic_root_model__", False) is True


@dataclass(frozen=True)
class PydanticModelInfo:
    pydantic_version: Literal["1", "2"]
    field_definitions: dict[str, FieldDefinition]
    model_fields: dict[str, pydantic.fields.FieldInfo]  # pyright: ignore[reportInvalidTypeForm,reportGeneralTypeIssues]
    title: str | None = None
    example: Any | None = None
    is_generic: bool = False


_CreateFieldDefinition = Callable[..., FieldDefinition]


def _create_field_definition_v2(  # noqa: C901
    field_annotation: Any,
    *,
    field_info: pydantic.fields.FieldInfo,  # pyright: ignore[reportInvalidTypeForm,reportGeneralTypeIssues]
    **field_definition_kwargs: Any,
) -> FieldDefinition:
    kwargs: dict[str, Any] = {}
    examples: list[Any] = []
    field_meta: list[Any] = []

    if json_schema_extra := field_info.json_schema_extra:
        if callable(json_schema_extra):
            raise ValueError("Callables not supported for json_schema_extra")
        if json_schema_example := json_schema_extra.get("example"):
            del json_schema_extra["example"]
            examples.append(json_schema_example)
        if json_schema_examples := json_schema_extra.get("examples"):
            del json_schema_extra["examples"]
            examples.extend(json_schema_examples)  # type: ignore[arg-type]
    if field_examples := field_info.examples:
        examples.extend(field_examples)

    if examples:
        if not json_schema_extra:
            json_schema_extra = {}
        json_schema_extra["examples"] = examples

    if description := field_info.description:
        kwargs["description"] = description

    if title := field_info.title:
        kwargs["title"] = title

    for meta in field_info.metadata:
        if isinstance(meta, pydantic.types.StringConstraints):  # pyright: ignore[reportAttributeAccessIssue]
            kwargs["min_length"] = meta.min_length
            kwargs["max_length"] = meta.max_length
            kwargs["pattern"] = meta.pattern
            kwargs["lower_case"] = meta.to_lower
            kwargs["upper_case"] = meta.to_upper
        # forward other metadata
        else:
            field_meta.append(meta)

    if json_schema_extra:
        kwargs["schema_extra"] = json_schema_extra

    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    if kwargs:
        kwarg_definition = ParameterKwarg(**kwargs)
        field_meta.append(kwarg_definition)

    if field_meta:
        field_definition_kwargs["raw"] = field_annotation
        for meta in field_meta:
            field_annotation = Annotated[field_annotation, meta]

    return FieldDefinition.from_annotation(
        annotation=field_annotation,
        **field_definition_kwargs,
    )


def get_model_info(
    annotation: Any,
    prefer_alias: bool = False,
) -> PydanticModelInfo:
    model: type[pydantic.BaseModel]  # pyright: ignore[reportInvalidTypeForm,reportGeneralTypeIssues]

    if is_generic(annotation):
        is_generic_model = True
        model = pydantic_unwrap_and_get_origin(annotation) or annotation
    else:
        is_generic_model = False
        model = annotation

    model_config = model.model_config
    model_field_info = model.model_fields
    title = model_config.get("title")
    example = model_config.get("example")

    model_fields: dict[str, pydantic.fields.FieldInfo] = {  # pyright: ignore[reportInvalidTypeForm,reportGeneralTypeIssues]
        k: getattr(f, "field_info", f) for k, f in model_field_info.items()
    }

    # extract the annotations from the FieldInfo. This allows us to skip fields
    # which have been marked as private
    # if there's a default factory, we wrap the field in 'NotRequired', to signal
    # that it is not required
    model_annotations = {
        k: NotRequired[field_info.annotation] if field_info.default_factory else field_info.annotation  # type: ignore[union-attr]
        for k, field_info in model_fields.items()
    }

    if is_generic_model:
        # if the model is generic, resolve the type variables. We pass in the
        # already extracted annotations, to keep the logic of respecting private
        # fields consistent with the above
        model_annotations = pydantic_get_type_hints_with_generics_resolved(
            annotation, model_annotations=model_annotations, include_extras=True
        )

    property_fields = {
        field_info.alias if field_info.alias and prefer_alias else k: _create_field_definition_v2(
            field_annotation=model_annotations[k],
            name=field_info.alias if field_info.alias and prefer_alias else k,
            default=Empty
            if is_undefined_sentinel(field_info.default) or is_pydantic_undefined(field_info.default)
            else field_info.default,
            field_info=field_info,
        )
        for k, field_info in model_fields.items()
    }

    computed_field_definitions = create_field_definitions_for_computed_fields(
        model,  # type: ignore[arg-type]
        prefer_alias=prefer_alias,
    )
    property_fields.update(computed_field_definitions)

    return PydanticModelInfo(
        pydantic_version="2",
        title=title,
        example=example,
        field_definitions=property_fields,
        is_generic=is_generic_model,
        model_fields=model_fields,
    )
