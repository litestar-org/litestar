"""The contents of this file were adapted from:

https://github.com/piccolo-orm/piccolo/blob/master/tests/example_apps/music/piccolo_app.py
"""

from pathlib import Path

from piccolo.conf.apps import AppConfig

from tests.unit.test_contrib.test_piccolo_orm.tables import (
    Band,
    Concert,
    Manager,
    RecordingStudio,
    Venue,
)

CURRENT_DIRECTORY = Path(__file__).parent

APP_CONFIG = AppConfig(
    app_name="music",
    table_classes=[
        Manager,
        Band,
        Venue,
        Concert,
        RecordingStudio,
    ],
    migrations_folder_path=str(CURRENT_DIRECTORY / "piccolo_migrations"),
    commands=[],
)
