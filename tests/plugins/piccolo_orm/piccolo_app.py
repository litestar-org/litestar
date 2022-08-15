"""The contents of this file were adapted from:

https://github.com/piccolo-orm/piccolo/blob/master/tests/example_apps/music/piccolo_app.py
"""

import os

from piccolo.conf.apps import AppConfig

from tests.plugins.piccolo_orm.tables import (
    Band,
    Concert,
    Manager,
    RecordingStudio,
    Venue,
)

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

APP_CONFIG = AppConfig(
    app_name="music",
    table_classes=[
        Manager,
        Band,
        Venue,
        Concert,
        RecordingStudio,
    ],
    migrations_folder_path=os.path.join(CURRENT_DIRECTORY, "piccolo_migrations"),
    commands=[],
)
