import os
import warnings

from litestar.exceptions import LitestarWarning
from litestar.types import AnyCallable


def warn_implicit_sync_to_thread(source: AnyCallable, stacklevel: int = 2) -> None:
    if os.getenv("LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD") == "0":
        return

    warnings.warn(
        f"Use of a synchronous callable {source} without setting sync_to_thread is "
        "discouraged since synchronous callables can block the main thread if they "
        "perform blocking operations. If the callable is guaranteed to be non-blocking, "
        "you can set sync_to_thread=False to skip this warning, or set the environment"
        "variable LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD=0 to disable warnings of this "
        "type entirely.",
        category=LitestarWarning,
        stacklevel=stacklevel,
    )
