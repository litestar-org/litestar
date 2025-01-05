from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING

from litestar.exceptions import LitestarWarning

if TYPE_CHECKING:
    import re

    from litestar.types import AnyCallable, AnyGenerator


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


def warn_sync_to_thread_with_async_callable(source: AnyCallable, stacklevel: int = 2) -> None:
    if os.getenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_ASYNC") == "0":
        return

    warnings.warn(
        f"Use of an asynchronous callable {source} with sync_to_thread; sync_to_thread "
        "has no effect on async callable. You can disable this warning by setting "
        "LITESTAR_WARN_SYNC_TO_THREAD_WITH_ASYNC=0",
        category=LitestarWarning,
        stacklevel=stacklevel,
    )


def warn_sync_to_thread_with_generator(source: AnyGenerator, stacklevel: int = 2) -> None:
    if os.getenv("LITESTAR_WARN_SYNC_TO_THREAD_WITH_GENERATOR") == "0":
        return

    warnings.warn(
        f"Use of generator {source} with sync_to_thread; sync_to_thread has no effect "
        "on generators. You can disable this warning by setting "
        "LITESTAR_WARN_SYNC_TO_THREAD_WITH_GENERATOR=0",
        category=LitestarWarning,
        stacklevel=stacklevel,
    )


def warn_pdb_on_exception(stacklevel: int = 2) -> None:
    warnings.warn("Python Debugger on exception enabled", category=LitestarWarning, stacklevel=stacklevel)


def warn_middleware_excluded_on_all_routes(
    pattern: re.Pattern,
    middleware_cls: type | None = None,
) -> None:
    middleware_name = f" {middleware_cls.__name__!r}" if middleware_cls else ""
    warnings.warn(
        f"Middleware{middleware_name} exclude pattern {pattern.pattern!r} greedily "
        "matches all paths, effectively disabling this middleware. If this was "
        "intentional, consider removing this middleware entirely",
        category=LitestarWarning,
        stacklevel=2,
    )


def warn_signature_namespace_override(signature_key: str, stacklevel: int = 2) -> None:
    if os.getenv("LITESTAR_WARN_SIGNATURE_NAMESPACE_OVERRIDE") == "0":
        return

    warnings.warn(
        f"Type '{signature_key}' is already defined as a different type in the signature namespace"
        "If this is intentional, you can disable this warning by setting "
        "LITESTAR_WARN_SIGNATURE_NAMESPACE_OVERRIDE=0",
        category=LitestarWarning,
        stacklevel=stacklevel,
    )
