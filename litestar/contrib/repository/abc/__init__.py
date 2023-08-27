from litestar.utils import warn_deprecation


def __getattr__(attr_name: str) -> object:
    from litestar.repository import abc

    for k in abc.__all__:
        warn_deprecation(
            deprecated_name=f"litestar.contrib.repository.abc.{k}",
            version="2.1",
            kind="import",
            removal_in="3.0",
            info=f"importing {attr_name} from 'litestar.contrib.repository.abc' is deprecated, please"
            f"import it from 'litestar.repository.abc' instead",
        )

        value = globals()[attr_name] = getattr(abc, k)
        return value

    raise AttributeError(f"module {__name__!r} has no attribute {attr_name!r}")
