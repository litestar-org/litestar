import pytest


@pytest.fixture
def user_data() -> dict:
    return {"id": "a3cad591-5b01-4341-ae8f-94f78f790674", "name": "Litestar User"}
