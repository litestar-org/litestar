from typing import Any

from litestar.utils import warn_deprecation


def __getattr__(attr_name: str) -> object:
    if "DataclassDTO" in attr_name:
        from litestar.dto import DataclassDTO

        value: Any = DataclassDTO
    elif "AbstractDTOFactory" in attr_name:
        from litestar.dto.base_factory import AbstractDTOFactory

        value = AbstractDTOFactory
    elif "DTOData" in attr_name:
        from litestar.dto import DTOData

        value = DTOData
    elif "DTOConfig" in attr_name:
        from litestar.dto import DTOConfig

        value = DTOConfig

    elif "DTOField" in attr_name:
        from litestar.dto import DTOField

        value = DTOField

    elif "Mark" in attr_name:
        from litestar.dto import Mark

        value = Mark
    elif "dto_field" in attr_name:
        from litestar.dto import dto_field

        value = dto_field
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")

    warn_deprecation(
        deprecated_name=f"litestar.dto.factory.{attr_name}",
        version="2.0b3",
        kind="import",
        removal_in="2.0",
        info=f"importing {attr_name} from 'litestar.dto.factory' is deprecated, please"
        f"import it from 'litestar.dto' instead",
    )

    globals()[attr_name] = value
    return value
