import sys
from importlib import reload
from pathlib import Path
from types import ModuleType

import pytest

from litestar.testing import TestClient

try:
    import piccolo  # noqa: F401
except ImportError:
    pytest.skip("Piccolo not installed", allow_module_level=True)

from docs.examples.contrib.piccolo import app as _app_module
from piccolo.testing.model_builder import ModelBuilder

pytestmark = [
    pytest.mark.xdist_group("piccolo"),
    pytest.mark.skipif(
        sys.platform != "linux",
        reason="piccolo ORM itself is not tested against windows and macOS",
    ),
]


@pytest.fixture()
def app_module() -> ModuleType:
    return reload(_app_module)


@pytest.fixture(autouse=True)
def create_test_data(app_module: ModuleType) -> None:
    db_path = Path(app_module.DB.path)
    db_path.unlink(missing_ok=True)
    app_module.Task.create_table(if_not_exists=True).run_sync()
    ModelBuilder.build_sync(app_module.Task)
    yield
    app_module.Task.alter().drop_table().run_sync()
    db_path.unlink()


def test_get_tasks(app_module):
    with TestClient(app=app_module.app) as client:
        response = client.get("/tasks")
        assert response.status_code == 200
        assert len(response.json()) == 1


def test_task_crud(app_module):
    with TestClient(app=app_module.app) as client:
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

        task = app_module.Task.select().first().run_sync()

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
