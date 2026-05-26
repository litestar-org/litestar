from litestar import Litestar, MediaType, Request, Response, get


def attach_user(request: Request) -> None:
    request.state["user"] = "alice"


def wrap_text_responses(response: Response) -> Response:
    if response.media_type == MediaType.TEXT:
        return Response({"value": response.content})
    return response


@get("/hello", sync_to_thread=False)
def hello(request: Request) -> str:
    return f"hello, {request.state['user']}"


app = Litestar(
    route_handlers=[hello],
    before_request=attach_user,
    after_request=wrap_text_responses,
)
