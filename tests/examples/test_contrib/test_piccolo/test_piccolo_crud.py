from pathlib import Path

import pytest

from litestar.testing import TestClient

try:
    import piccolo  # noqa: F401
except ImportError:
    pytest.skip("Piccolo not installed", allow_module_level=True)

from docs.examples.contrib.piccolo.app import DB, Task, app
from piccolo.testing.model_builder import ModelBuilder

pytestmark = pytest.mark.xdist_group("piccolo")


@pytest.fixture(autouse=True, scope="module")
def create_test_data():
    Task.create_table(if_not_exists=True).run_sync()
    ModelBuilder.build_sync(Task)
    yield
    Task.alter().drop_table().run_sync()
    Path(DB.path).unlink()


def test_get_tasks():
    with TestClient(app=app) as client:
        response = client.get("/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_task_crud():
    with TestClient(app=app) as client:
        payload = {
            "name": "Task 1",
            "completed": False,
        }

        response = client.post(
            "/tasks",
            json=payload,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Task 1"

        response = client.get("/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 2

        task = Task.select().first().run_sync()

        payload = {
            "id": task["id"],
            "name": "Task 2",
            "completed": True,
        }

        response = client.patch(
            f"/tasks/{task['id']}",
            json=payload,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Task 2"
        assert response.json()["completed"] is True

        response = client.delete(
            f"/tasks/{task['id']}",
        )
        assert response.status_code == 204

        response = client.get("/tasks")
        assert response.status_code == 200
        assert response.json()[0]["name"] == "Task 1"
        assert len(response.json()) == 1
