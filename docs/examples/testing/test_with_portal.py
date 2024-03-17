from concurrent.futures import Future, wait

import anyio

from litestar.testing import create_test_client


def test_with_portal() -> None:
    """This example shows how to manage asynchronous tasks using a portal.

    The test function itself is not async.
    Asynchronous functions are executed and awaited using the portal.
    """

    async def get_float(value: float) -> float:
        await anyio.sleep(value)
        return value

    with create_test_client(
        route_handlers=[]
    ) as test_client, test_client.portal() as portal:
        # start a background task with the portal
        future: Future[float] = portal.start_task_soon(get_float, 0.25)
        # do other work
        assert portal.call(get_float, 0.1) == 0.1
        # wait for the background task to complete
        wait([future])
        assert future.done()
        assert future.result() == 0.25
