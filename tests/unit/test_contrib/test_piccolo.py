from __future__ import annotations

import litestar_piccolo
import pytest
from piccolo.columns.column_types import Varchar
from piccolo.table import Table


class Manager(Table):
    name = Varchar(length=50)


def test_dto_deprecation() -> None:
    with pytest.deprecated_call():
        from litestar.contrib.piccolo import PiccoloDTO

        _ = PiccoloDTO[Manager]


def test_repository_re_exports() -> None:
    from litestar.contrib.piccolo import PiccoloDTO

    assert PiccoloDTO is litestar_piccolo.PiccoloDTO
