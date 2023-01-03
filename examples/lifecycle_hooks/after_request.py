from starlite import Starlite, Response


async def my_after_request_handler(response: Response) -> Response:
    ...


app = Starlite(route_handlers=[...], after_request=my_after_request_handler)