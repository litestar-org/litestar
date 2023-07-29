"""The contents of this file were adapted from:

https://github.com/piccolo-orm/piccolo/blob/master/tests/example_apps/music/tables.py
"""

from piccolo.columns.column_types import JSON, JSONB, Array, ForeignKey, Integer, Varchar
from piccolo.table import Table


class RecordingStudio(Table):
    facilities = JSON()
    facilities_b = JSONB()
    microphones = Array(Varchar())


class Manager(Table):
    name = Varchar(length=50)


class Band(Table):
    name = Varchar(length=50)
    manager = ForeignKey(Manager)
    popularity = Integer()


class Venue(Table):
    name = Varchar(length=100)
    capacity = Integer(secret=True)


class Concert(Table):
    band_1 = ForeignKey(Band)
    band_2 = ForeignKey(Band)
    venue = ForeignKey(Venue)
