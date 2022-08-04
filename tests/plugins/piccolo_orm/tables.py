"""
This file was copied from: https://github.com/piccolo-orm/piccolo/blob/master/tests/example_apps/music/tables.py
"""

from enum import Enum

from piccolo.columns.column_types import (
    JSON,
    JSONB,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Varchar,
)
from piccolo.columns.readable import Readable
from piccolo.table import Table

###############################################################################
# Simple example


class Manager(Table):
    name = Varchar(length=50)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


class Band(Table):
    name = Varchar(length=50)
    manager = ForeignKey(Manager)
    popularity = Integer()

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


###############################################################################
# More complex


class Venue(Table):
    name = Varchar(length=100)
    capacity = Integer(secret=True)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


class Concert(Table):
    band_1 = ForeignKey(Band)
    band_2 = ForeignKey(Band)
    venue = ForeignKey(Venue)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(
            template="%s and %s at %s, capacity %s",
            columns=[
                cls.band_1.name,
                cls.band_2.name,
                cls.venue.name,
                cls.venue.capacity,
            ],
        )


class Ticket(Table):
    concert = ForeignKey(Concert)
    price = Numeric(digits=(5, 2))


class Poster(Table, tags=["special"]):
    """
    Has tags for tests which need it.
    """

    content = Text()


class Shirt(Table):
    """
    Used for testing columns with a choices attribute.
    """

    class Size(str, Enum):
        small = "s"
        medium = "m"
        large = "l"

    size = Varchar(length=1, choices=Size, default=Size.large)


class RecordingStudio(Table):
    """
    Used for testing JSON and JSONB columns.
    """

    facilities = JSON()
    facilities_b = JSONB()
