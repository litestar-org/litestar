from litestar import get


@get(sync_to_thread=False)
def handler() -> None: ...


# or


@get(sync_to_thread=True)
def handler_sync() -> None: ...
