from litestar.utils import warn_deprecation


def __getattr__(attr_name: str) -> object:
    from litestar.repository import exceptions

    for k in exceptions.__all__:
        warn_deprecation(
            deprecated_name=f"litestar.repository.contrib.exceptions.{k}",
            version="2.1",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.repository.exceptions' is deprecated, please"
            f"import it from 'litestar.repository.exceptions' instead",
        )

        value = globals()[attr_name] = getattr(exceptions, k)
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
