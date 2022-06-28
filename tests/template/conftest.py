import pathlib

import pytest


@pytest.fixture
def template_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path
