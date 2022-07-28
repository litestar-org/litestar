"""
File is copied from https://github.com/piccolo-orm/piccolo/blob/master/tests/example_apps/music/tables_detailed.py
"""
from datetime import timedelta
from enum import Enum

from piccolo.columns import (
    JSON,
    JSONB,
    UUID,
    BigInt,
    Boolean,
    Bytea,
    Date,
    ForeignKey,
    Integer,
    Interval,
    Numeric,
    SmallInt,
    Text,
    Timestamp,
    Timestamptz,
    Varchar,
)
from piccolo.columns.readable import Readable
from piccolo.table import Table

###############################################################################
# Simple example


class Manager(Table):
    name = Varchar(length=50)
    touring = Boolean()

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.name])


class Band(Table):
    label_id = UUID()
    date_signed = Date()
    name = Varchar(length=50)
    manager = ForeignKey(Manager)
    popularity = Integer()


###############################################################################
# More complex


class Venue(Table):
    name = Varchar(length=100)
    capacity = Integer()


class Concert(Table):
    band_1 = ForeignKey(Band)
    band_2 = ForeignKey(Band)
    venue = ForeignKey(Venue)

    duration = Interval(default=timedelta(weeks=5, days=3))
    net_profit = SmallInt(default=-32768)


class Ticket(Table):
    concert = ForeignKey(Concert)
    price = Numeric(digits=(5, 2))
    purchase_time = Timestamp()
    purchase_time_tz = Timestamptz()


class Poster(Table, tags=["special"]):
    """
    Has tags for tests which need it.
    """

    image = Bytea(default=b"\xbd\x78\xd8")
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

    facilities = JSON(default={"amplifier": False, "microphone": True})
    facilities_b = JSONB()
    records = BigInt(default=9223372036854775807)