from litestar import Litestar, MediaType, get


@get("/json", sync_to_thread=False)
def get_json() -> dict[str, str]:
    return {"hello": "world"}


@get("/text", media_type=MediaType.TEXT, sync_to_thread=False)
def get_text() -> str:
    return "hello, world"


@get("/html", media_type=MediaType.HTML, sync_to_thread=False)
def get_html() -> str:
    return "<strong>hello, world</strong>"


app = Litestar(route_handlers=[get_json, get_text, get_html])
