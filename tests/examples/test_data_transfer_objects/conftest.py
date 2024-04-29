from __future__ import annotations

import pytest


@pytest.fixture
def user_data() -> dict:
    return {"name": "Mr Sunglass", "email": "mr.sunglass@example.com", "age": 30}
