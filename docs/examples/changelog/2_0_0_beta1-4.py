async def after_exception_handler(exc: Exception, scope: Scope) -> None:
    state = scope["app"].state
