from typing import List

from starlette.status import HTTP_200_OK

from starlite import BackgroundTask, BackgroundTasks, create_test_client, get


async def test_background_tasks() -> None:
    values: List[int] = []

    def extend_values(values_to_extend: List[int]) -> None:
        values.extend(values_to_extend)

    tasks = BackgroundTasks(
        [BackgroundTask(extend_values, [1, 2, 3]), BackgroundTask(extend_values, values_to_extend=[4, 5, 6])]
    )

    @get("/", background=tasks)
    def handler() -> None:
        return None

    with create_test_client(handler) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK
        assert values == [1, 2, 3, 4, 5, 6]
