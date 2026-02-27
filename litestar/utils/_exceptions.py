import sys

if sys.version_info <= (3, 11):
    from exceptiongroup import ExceptionGroup


def _collapse_exception_groups(exc: Exception) -> Exception:
    while isinstance(exc, ExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc
