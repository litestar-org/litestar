from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine

DB = SQLiteEngine(path="../test.sqlite")

APP_REGISTRY = AppRegistry(
    apps=[
        "tests.unit.test_contrib.test_piccolo_orm.piccolo_app",
    ],
)
