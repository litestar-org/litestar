import random
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from starlite import Response


async def slow_handler() -> dict:
    output = {}
    count = 0
    while count < 1000:
        output[str(count)] = random.random()
        count += 1
    return output


def after_request_handler(response: "Response") -> "Response":
    response.headers["unique-identifier"] = str(uuid4())
    return response
