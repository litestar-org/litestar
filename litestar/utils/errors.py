from typing import NoReturn

from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, KwargDefinition, ParameterKwarg


def _has_explicit_param_type(default: ParameterKwarg) -> bool:
    """Whether ``default.param_type`` reflects an explicit choice by the user.

    ``ParameterKwarg.param_type`` defaults to :attr:`ParamType.QUERY <litestar.enums.ParamType>` and
    is only reassigned when one of the ``header``/``cookie``/``query`` arguments is given. A plain
    ``Parameter()`` therefore reports ``QUERY`` even when it annotates a path parameter, since
    whether a parameter is a path parameter is decided by the route path rather than the annotation.
    The dedicated subclasses (:class:`~litestar.params.PathParameter` and friends) each set
    ``param_type`` themselves, so for those the value is meaningful.
    """
    return type(default) is not ParameterKwarg or any(
        value is not None for value in (default.header, default.cookie, default.query)
    )


def raise_for_kwarg_as_default(default: KwargDefinition) -> NoReturn:
    if isinstance(default, BodyKwarg):
        alternative = "Annotated[<type>, Body(...)]"
    elif isinstance(default, ParameterKwarg) and not default.is_constrained:
        if _has_explicit_param_type(default):
            alternative = {
                ParamType.QUERY: "FromQuery",
                ParamType.HEADER: "FromHeader",
                ParamType.COOKIE: "FromCookie",
                ParamType.PATH: "FromPath",
            }[default.param_type]
        else:
            alternative = "Annotated[<type>, Parameter(...)]"
    else:
        alternative = f"Annotated[<type>, {type(default).__name__}(...)]"
    msg = f"Usage of parameter defaults to declare metadata is no longer supported. Use '{alternative}' instead"
    raise ImproperlyConfiguredException(msg)
