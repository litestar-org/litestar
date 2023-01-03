from typing import Optional

from starlite import Request, Starlite, get, Response, MediaType


async def before_request_handler(request: Request) -> Optional[Response]:
    name = request.query_params.get("name", "Luke")
    if name == "Ben":
        return Response(
            "These are not the bytes you are looking for",
            media_type=MediaType.TEXT,
        )
    request.state["message"] = f"Use the handler, {name}"


@get("/")
async def handler(request: Request) -> str:
    return request.state.get("message")


app = Starlite(route_handlers=[handler], before_request=before_request_handler)

# run: /
# run: /?name=Ben
