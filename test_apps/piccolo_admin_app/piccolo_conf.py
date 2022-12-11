from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine

DB = SQLiteEngine(path="test.sqlite")

APP_REGISTRY = AppRegistry(
    apps=[
        "home.piccolo_app",
        "piccolo_admin.piccolo_app",
    ]
)
