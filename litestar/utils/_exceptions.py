def _collapse_exception_groups(exc: Exception) -> Exception:
    while isinstance(exc, ExceptionGroup) and len(exc.exceptions) == 1:
        exc = exc.exceptions[0]
    return exc
