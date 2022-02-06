import random
from uuid import uuid4

from starlite import Response, create_test_client, get


async def slow_hanlder() -> dict:
    output = {}
    count = 0
    while count < 100000:
        output[str(count)] = random.random()
        count += 1
    return output


def after_request_handler(response: Response) -> Response:
    response.headers["unique-identifier"] = str(uuid4())
    return response


def test_cache_response():
    with create_test_client(
        route_handlers=[get("/cached", cache=True)(slow_hanlder)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()
