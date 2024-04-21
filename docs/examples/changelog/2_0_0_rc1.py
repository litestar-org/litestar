async def my_generator() -> AsyncGenerator[bytes, None]:
    count = 0
    while count < 10:
        await sleep(0.01)
        count += 1
        yield str(count)


@get(path="/count")
def sse_handler() -> ServerSentEvent:
    return ServerSentEvent(my_generator())