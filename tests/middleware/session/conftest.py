import secrets
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from litestar.middleware.session.client_side import ClientSideSessionBackend


@pytest.fixture()
def session_test_cookies(cookie_session_backend: "ClientSideSessionBackend") -> str:
    # Put random data. If you are also handling session management then use session_middleware fixture and create
    # session cookies with your own data.
    _session = {"key": secrets.token_hex(16)}
    return "; ".join(
        f"session-{i}={serialize.decode('utf-8')}"
        for i, serialize in enumerate(cookie_session_backend.dump_data(_session))
    )
