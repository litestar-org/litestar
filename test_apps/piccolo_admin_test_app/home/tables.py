from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Boolean, ForeignKey, Timestamp, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table
from piccolo_conf import DB


class Task(Table, db=DB):
    """An example table."""

    name = Varchar()
    completed = Boolean()
    created_at = Timestamp()
    task_user = ForeignKey(BaseUser)

    @classmethod
    def get_readable(cls) -> Readable:
        return Readable(template="%s", columns=[cls.task_user.username])
