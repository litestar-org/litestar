"""Base class that aggregates slots for all SQLAlchemy plugins.

See: https://stackoverflow.com/questions/53060607/python-3-6-5-multiple-bases-have-instance-lay-out-conflict-when-multi-inherit
"""
from __future__ import annotations


class SlotsBase:
    __slots__ = (
        "_config",
        "_type_dto_map",
    )
