# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from litestar.connection import ASGIConnection
from litestar.datastructures import Headers, ImmutableState
from litestar.di._helpers import _describe_callable
from litestar.di.exceptions import DIRegistrationError
from litestar.enums import ParamType
from litestar.params import BodyKwarg, ParameterKwarg, QueryParams, RawBody, RequestCookies
from litestar.types import Scope

if TYPE_CHECKING:
    from litestar.di.provider import DependencyKey
    from litestar.typing import FieldDefinition

__all__ = ("RequestParameter",)


@dataclass(frozen=True, slots=True)
class RequestParameter:
    """Parameter of a Provider or InjectionTarget declared by a parameter marker, such
    as ``FromQuery[...]``, or a body marker, such as ``JSONBody[...]``
    """

    parameter_name: str
    """Name of the parameter on the callable"""

    param_type: ParamType | None
    """Type of the request parameter. ``None`` for the request body"""

    name: str
    """Name of the request parameter in the request, as declared. Empty for the request body"""

    field_definition: FieldDefinition
    """The parameter's declaration. Its ``kwarg_definition`` is the marker"""

    @property
    def is_body(self) -> bool:
        """Whether a body marker declares the parameter"""
        return self.param_type is None

    @property
    def key(self) -> str:
        """The dependency key, ``"<param type>:<name>"`` with a header's name lower-cased, or
        ``"body:"`` for the request body
        """
        if self.param_type is None:
            return "body:"
        name = self.name.lower() if self.param_type is ParamType.HEADER else self.name
        return f"{self.param_type.value}:{name}"


_RESERVED_REQUEST_VALUE_TYPES: Final = (Headers, QueryParams, RequestCookies, Scope, RawBody)
"""Annotations of the reserved request values, besides connection and state classes"""


def _reserved_request_value_key(field: FieldDefinition) -> DependencyKey | None:
    """Return the key of the reserved request value ``field``'s annotation names: the type, with a
    parameterised class keyed by its class (``Request[Any, Any, State]`` by ``Request``). ``None``
    if it names none
    """
    if field.annotation in _RESERVED_REQUEST_VALUE_TYPES:
        return field.annotation  # type: ignore[no-any-return]
    if not field.is_union and field.is_subclass_of((ASGIConnection, ImmutableState)):
        return field.type_  # type: ignore[no-any-return]
    return None


def _request_parameter_for(name: str, field: FieldDefinition) -> RequestParameter | None:
    kwarg = field.kwarg_definition
    if isinstance(kwarg, ParameterKwarg):
        return RequestParameter(
            parameter_name=name, param_type=kwarg.param_type, name=kwarg.name or name, field_definition=field
        )
    if isinstance(kwarg, BodyKwarg):
        return RequestParameter(parameter_name=name, param_type=None, name="", field_definition=field)
    return None


def _request_dependency(
    fn: Any, name: str, field: FieldDefinition
) -> tuple[DependencyKey, RequestParameter | None] | None:
    """Return the key of the value of the request the parameter ``name`` declares, with
    its :class:`RequestParameter` if it has a parameter or body marker. ``None`` if it
    doesn't declare one.

    Without a marker, the annotation declares a reserved request value, with its type
    becoming the key (e.g. ``Request[Any, Any, State]`` will use ``Request`` as a type
    key)
    """
    request_parameter = _request_parameter_for(name, field)
    if request_parameter is not None:
        return request_parameter.key, request_parameter

    member_markers = [
        member.kwarg_definition
        for member in (field.inner_types if field.is_union else ())
        if isinstance(member.kwarg_definition, (ParameterKwarg, BodyKwarg))
    ]
    if member_markers:
        raise DIRegistrationError(
            f"Parameter {name!r} of {_describe_callable(fn)} carries a {type(member_markers[0]).__name__} "
            "marker on a member of its union annotation. The marker must be on the whole annotation"
        )

    key = _reserved_request_value_key(field)
    return None if key is None else (key, None)
