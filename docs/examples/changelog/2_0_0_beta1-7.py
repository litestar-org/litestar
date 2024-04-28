async def before_send_hook_handler(message: Message, scope: Scope) -> None:
    state = scope["app"].state
