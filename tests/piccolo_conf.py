from piccolo.conf.apps import AppRegistry
from piccolo.engine import SQLiteEngine

DB = SQLiteEngine(path="test.sqlite")

APP_REGISTRY = AppRegistry(apps=["tests.contrib.piccolo_orm.piccolo_app"])
