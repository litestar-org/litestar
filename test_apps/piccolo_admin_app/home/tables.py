from piccolo.apps.user.tables import BaseUser
from piccolo.columns import Boolean, ForeignKey, Timestamp, Varchar
from piccolo.columns.readable import Readable
from piccolo.table import Table


class Task(Table):
    """An example table."""

    name = Varchar()
    completed = Boolean(default=False)
    created_at = Timestamp()
    task_user = ForeignKey(BaseUser)

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.task_user.username])
