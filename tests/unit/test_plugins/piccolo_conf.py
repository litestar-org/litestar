from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine

DB = SQLiteEngine(path=":memory:", check_same_thread=False)

APP_REGISTRY = AppRegistry(
    apps=[
        "tests.unit.test_plugins.test_piccolo.piccolo_app",
    ],
)
