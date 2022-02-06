import random
from datetime import datetime, timedelta
from uuid import uuid4

from freezegun import freeze_time

from starlite import Request, Response, create_test_client, get


async def slow_handler() -> dict:
    output = {}
    count = 0
    while count < 1000:
        output[str(count)] = random.random()
        count += 1
    return output


def after_request_handler(response: Response) -> Response:
    response.headers["unique-identifier"] = str(uuid4())
    return response


def test_default_cache_response():
    with create_test_client(
        route_handlers=[get("/cached", cache=True)(slow_handler)], after_request=after_request_handler
    ) as client:
        first_response = client.get("/cached")
        first_response_identifier = first_response.headers["unique-identifier"]
        assert first_response_identifier
        second_response = client.get("/cached")
        assert second_response.headers["unique-identifier"] == first_response_identifier
        assert first_response.json() == second_response.json()


def test_expiration():
    now = datetime.now()
    with freeze_time(now) as frozen_datetime:
        # test the default expiration
        with create_test_client(
            route_handlers=[get("/cached", cache=True)(slow_handler)], after_request=after_request_handler
        ) as client:
            first_response = client.get("/cached")
            frozen_datetime.tick()
            now += timedelta(seconds=60)
            second_response = client.get("/cached")
            assert first_response.json() == second_response.json()
            frozen_datetime.tick()
            now += timedelta(seconds=1)
            third_response = client.get("/cached")
            assert first_response.json() != third_response.json()
        # test handler expiration
        with create_test_client(
            route_handlers=[get("/cached", cache=10)(slow_handler)], after_request=after_request_handler
        ) as client:
            first_response = client.get("/cached")
            frozen_datetime.tick()
            now += timedelta(seconds=10)
            second_response = client.get("/cached")
            assert first_response.json() == second_response.json()
            frozen_datetime.tick()
            now += timedelta(seconds=1)
            third_response = client.get("/cached")
            assert first_response.json() != third_response.json()


def test_cache_key():
    def custom_cache_key_builder(request: Request) -> str:
        return request.url.path + ":::cached"

    with create_test_client(
        route_handlers=[get("/cached", cache=True, cache_key_builder=custom_cache_key_builder)(slow_handler)]
    ) as client:
        client.get("/cached")
        assert client.app.cache_config.backend.get("/cached:::cached")
