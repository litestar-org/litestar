from typing import NoReturn

from litestar.enums import ParamType
from litestar.exceptions import ImproperlyConfiguredException
from litestar.params import BodyKwarg, KwargDefinition, ParameterKwarg


def raise_for_kwarg_as_default(default: KwargDefinition) -> NoReturn:
    if isinstance(default, BodyKwarg):
        alternative = "Annotated[<type>, Body(...)]"
    elif (
        isinstance(default, ParameterKwarg)
        and not default.is_constrained
        # 'param_type' is only set on subclasses of 'ParameterKwarg'
        and (param_type := getattr(default, "param_type", None)) is not None
    ):
        alternative = {
            ParamType.QUERY: "FromQuery",
            ParamType.HEADER: "FromHeader",
            ParamType.COOKIE: "FromCookie",
            ParamType.PATH: "FromPath",
        }[param_type]
    else:
        alternative = f"Annotated[<type>, {type(default).__name__}(...)]"
    msg = f"Usage of parameter defaults to declare metadata is no longer supported. Use '{alternative}' instead"
    raise ImproperlyConfiguredException(msg)
