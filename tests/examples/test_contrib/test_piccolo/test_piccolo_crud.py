import os
from pathlib import Path
from unittest import TestCase

import pytest

from litestar.testing import TestClient

os.environ["PICCOLO_CONF"] = "docs.examples.contrib.piccolo.piccolo_conf"

try:
    import piccolo  # noqa: F401
except ImportError:
    pytest.skip("Piccolo not installed", allow_module_level=True)

from docs.examples.contrib.piccolo.app import Task, app  # noqa: E402
from piccolo.testing.model_builder import ModelBuilder  # noqa: E402


@pytest.mark.xdist_group("examples-piccolo")
class TestCrud(TestCase):
    def setUp(self):
        Task.create_table(if_not_exists=True).run_sync()
        ModelBuilder.build_sync(Task)

    def tearDown(self):
        Task.alter().drop_table().run_sync()
        from docs.examples.contrib.piccolo.piccolo_conf import DB

        Path(DB.path).unlink()

    def test_get_tasks(self):
        with TestClient(app=app) as client:
            response = client.get("/tasks")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 1)

    def test_task_crud(self):
        with TestClient(app=app) as client:
            payload = {
                "name": "Task 1",
                "completed": False,
            }

            response = client.post(
                "/tasks",
                json=payload,
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["name"], "Task 1")

            response = client.get("/tasks")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()), 2)

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
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], "Task 2")
            self.assertEqual(response.json()["completed"], True)

            response = client.delete(
                f"/tasks/{task['id']}",
            )
            self.assertEqual(response.status_code, 204)

            response = client.get("/tasks")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()[0]["name"], "Task 1")
            self.assertEqual(len(response.json()), 1)
