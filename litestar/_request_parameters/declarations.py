from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Final

from litestar.di._request import _request_parameter_for
from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import ParameterKwarg
from litestar.types import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

    from litestar.di import RequestParameter
    from litestar.params import BodyKwarg
    from litestar.utils.signature import ParsedSignature

__all__ = ("RequestParameterDefinition", "apply_layer_parameters", "merge_request_parameters")


@dataclasses.dataclass(frozen=True)
class RequestParameterDefinition:
    """A request parameter, or the request body, merged from all the parameters declaring it"""

    key: str
    """Key of the dependency, as :attr:`~litestar.di.RequestParameter.key`"""

    param_type: ParamType | None
    """Type of the parameter. ``None`` for the request body"""

    name: str
    """Name of the parameter in the request. Empty for the body"""

    field_definition: FieldDefinition
    """The merged declarations"""

    marker: ParameterKwarg | BodyKwarg
    """The parameter marker or body marker of the merged declarations"""

    @property
    def is_body(self) -> bool:
        """Whether this is the request body"""
        return self.param_type is None


_FIELDS_NOT_COMPARED: Final = frozenset({"name", "annotation"})
"""Fields of a declaration that are compared as part of the key or the type"""


@dataclasses.dataclass(frozen=True)
class _Declaration:
    owner: str | None
    """The callable declaring the parameter, ``None`` for a layer parameter"""

    parameter: RequestParameter

    @property
    def field_definition(self) -> FieldDefinition:
        return self.parameter.field_definition

    @property
    def declares_type(self) -> bool:
        kwarg_definition = self.field_definition.kwarg_definition
        # a layer parameter without 'annotation=' has no declared type
        return not (
            self.owner is None and isinstance(kwarg_definition, ParameterKwarg) and kwarg_definition.annotation is Empty
        )

    @property
    def declares_default(self) -> bool:
        # a layer parameter cannot declare a default
        return self.owner is not None

    def __str__(self) -> str:
        if self.owner is None:
            return f"layer parameter {self.parameter.parameter_name!r}"
        return f"parameter {self.parameter.parameter_name!r} of {self.owner}"


def _format_type(annotation: Any) -> str:
    return annotation.__name__ if isinstance(annotation, type) else repr(annotation)


def _describe_source(param_type: ParamType | None, name: str) -> str:
    return "the request body" if param_type is None else f"the {param_type.value} parameter {name!r}"


def _describe_default(default: Any) -> str:
    return "no default" if default is Empty else f"default {default!r}"


def _mismatch(
    source: str, one: _Declaration, other: _Declaration, one_description: str, other_description: str
) -> ImproperlyConfiguredException:
    return ImproperlyConfiguredException(
        f"{one} and {other} declare {source} differently: {one_description} and {other_description}"
    )


def _merge_declarations(source: str, declarations: list[_Declaration]) -> FieldDefinition:
    """Return the declaration of a parameter declared by all of ``declarations``.

    Raises:
        ImproperlyConfiguredException: If two of ``declarations`` declare a different type,
            default, constraint or other field.
    """
    first = declarations[0]
    typed = next((declaration for declaration in declarations if declaration.declares_type), first)
    defaulted = next((declaration for declaration in declarations if declaration.declares_default), None)
    kwarg_definition = first.parameter.marker
    compared = [field.name for field in dataclasses.fields(kwarg_definition) if field.name not in _FIELDS_NOT_COMPARED]
    for other in declarations[1:]:
        if other.declares_type and other.field_definition.annotation != typed.field_definition.annotation:
            raise _mismatch(
                source,
                typed,
                other,
                f"type {_format_type(typed.field_definition.annotation)!r}",
                f"type {_format_type(other.field_definition.annotation)!r}",
            )
        if (
            defaulted is not None
            and other.declares_default
            and other.field_definition.default != defaulted.field_definition.default
        ):
            raise _mismatch(
                source,
                defaulted,
                other,
                _describe_default(defaulted.field_definition.default),
                _describe_default(other.field_definition.default),
            )
        other_kwarg_definition = other.field_definition.kwarg_definition
        for name in compared:
            if (value := getattr(kwarg_definition, name)) != (other_value := getattr(other_kwarg_definition, name)):
                raise _mismatch(source, first, other, f"{name} {value!r}", f"{name} {other_value!r}")

    return dataclasses.replace(
        typed.field_definition,
        kwarg_definition=kwarg_definition,
        default=defaulted.field_definition.default if defaulted is not None else Empty,
    )


def _binds_layer_parameter(field: FieldDefinition, layer_parameter: FieldDefinition) -> bool:
    kwarg_definition = field.kwarg_definition
    return (
        isinstance(kwarg_definition, ParameterKwarg)
        and kwarg_definition.param_type is layer_parameter.kwarg_definition.param_type  # type: ignore[union-attr]
        and all(
            getattr(kwarg_definition, kwarg_field.name) == kwarg_field.default
            for kwarg_field in dataclasses.fields(kwarg_definition)
        )
    )


def apply_layer_parameters(
    signature: ParsedSignature, layer_parameters: Mapping[str, FieldDefinition]
) -> ParsedSignature:
    """Return ``signature`` with each parameter that binds a layer parameter carrying that layer
    parameter's declaration, ``signature`` itself if no parameter binds one.

    A parameter binds the layer parameter of its name if its marker is of the layer parameter's
    type and sets no field, e.g. ``FromQuery[int]``.

    Args:
        signature: The signature of a callable
        layer_parameters: The layer parameters, by name
    """
    bound = {
        name: FieldDefinition.from_kwarg(
            annotation=field.raw,
            name=name,
            default=field.default,
            kwarg_definition=layer_parameters[name].kwarg_definition,
        )
        for name, field in signature.parameters.items()
        if name in layer_parameters and _binds_layer_parameter(field, layer_parameters[name])
    }
    return dataclasses.replace(signature, parameters={**signature.parameters, **bound}) if bound else signature


def merge_request_parameters(
    request_parameters: Mapping[str, Iterable[RequestParameter]],
    *,
    layer_parameters: Mapping[str, FieldDefinition],
    paths: Mapping[str, Collection[str]],
) -> dict[str, RequestParameterDefinition]:
    """Return the request parameters of a handler, by key, each merged from the parameters and
    layer parameters declaring it.

    Args:
        request_parameters: The request parameters of each callable, by a description of the
            callable used in error messages
        layer_parameters: The layer parameters, by name
        paths: The names of the path parameters of each of the handler's paths, by path

    Raises:
        ImproperlyConfiguredException: If the declarations of a parameter differ, a parameter
            declares a request parameter that is neither required nor has a default, a
            required path parameter is missing from one of ``paths``, or only layer parameters
            without ``annotation`` declare a request parameter.
    """
    declarations: dict[str, list[_Declaration]] = {}
    for name, field in layer_parameters.items():
        layer_parameter = _request_parameter_for(name, field)
        if layer_parameter is None:
            raise ImproperlyConfiguredException(f"Layer parameter {name!r} declares no parameter type")
        declarations.setdefault(layer_parameter.key, []).append(_Declaration(owner=None, parameter=layer_parameter))
    for owner, parameters in request_parameters.items():
        for parameter in parameters:
            declarations.setdefault(parameter.key, []).append(_Declaration(owner=owner, parameter=parameter))

    definitions: dict[str, RequestParameterDefinition] = {}
    for key, key_declarations in declarations.items():
        param_type, name = key_declarations[0].parameter.param_type, key_declarations[0].parameter.name
        source = _describe_source(param_type, name)
        field_definition = _merge_declarations(source, key_declarations)
        declarers = f"{' and '.join(map(str, key_declarations))} declare{'s' if len(key_declarations) == 1 else ''}"
        if not any(declaration.declares_type for declaration in key_declarations):
            raise ImproperlyConfiguredException(
                f"{declarers} {source} without 'annotation', and no parameter of the handler or its "
                "dependencies declares it"
            )
        # a layer parameter cannot declare a default; a parameter receiving the value must
        if (
            not field_definition.is_required
            and not field_definition.has_default
            and any(declaration.owner is not None for declaration in key_declarations)
        ):
            raise ImproperlyConfiguredException(f"{declarers} {source} not required but without a default")
        if param_type is ParamType.PATH and field_definition.is_required:
            for path in sorted(paths):
                if name not in paths[path]:
                    raise ImproperlyConfiguredException(
                        f"{declarers} the required path parameter {name!r}, which the route {path!r} does not have"
                    )
        definitions[key] = RequestParameterDefinition(
            key=key,
            param_type=param_type,
            name=name,
            field_definition=field_definition,
            marker=key_declarations[0].parameter.marker,
        )
    return definitions
