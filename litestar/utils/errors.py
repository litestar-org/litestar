from typing import NoReturn

from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import KwargDefinition, ParameterKwarg


def raise_for_kwarg_as_default(default: KwargDefinition) -> NoReturn:
    alternative = f"Annotated[<type>, {type(default).__name__}(...)]"
    if isinstance(default, ParameterKwarg) and not default.is_constrained:
        alternative = {
            ParamType.QUERY: "FromQuery",
            ParamType.HEADER: "FromHeader",
            ParamType.COOKIE: "FromCookie",
            ParamType.PATH: "FromPath",
        }[default.param_type]
    msg = f"Usage of parameter defaults to declare metadata is no longer supported. Use '{alternative}' instead"
    raise ImproperlyConfiguredException(msg)
