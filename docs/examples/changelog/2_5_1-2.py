from litestar import get


@get("/stream")
async def stream(self) -> ServerSentEvent:
    async def gen() -> AsyncGenerator[str, None]:
        c = 0
        while True:
            yield f"<div>{c}</div>\n"
            c += 1

    return ServerSentEvent(gen(), event_type="my_event")
