from litestar.utils import warn_deprecation


def __getattr__(attr_name: str) -> object:
    if "DataclassDTO" in attr_name:
        from litestar.dto import DataclassDTO

        warn_deprecation(
            deprecated_name="litestar.dto.factory.stdlib.dataclass.DataclassDTO",
            version="2.0b3",
            kind="import",
            removal_in="2.0",
            info="importing 'DataclassDTO' from 'litestar.dto.factory.stdlib.dataclass' is deprecated, please"
            "import it from 'litestar.dto.factory' instead",
        )

        globals()[attr_name] = DataclassDTO
        return DataclassDTO
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
