from litestar.utils import warn_deprecation


def __getattr__(attr_name: str) -> object:
    if "MsgspecDTO" in attr_name:
        from litestar.dto.msgspec_dto_factory import MsgspecDTO

        warn_deprecation(
            deprecated_name="litestar.contrib.msgspec.MsgspecDTO",
            version="2.0b3",
            kind="import",
            removal_in="2.0",
            info="importing 'MsgspecDTO' from 'litestar.contrib.msgspec' is deprecated, please"
            "import it from 'litestar.dto.factory' instead",
        )

        globals()[attr_name] = MsgspecDTO
        return MsgspecDTO
    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
