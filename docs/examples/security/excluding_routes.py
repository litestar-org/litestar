from uuid import UUID

from pydantic import BaseModel, EmailStr

from litestar.middleware.session.server_side import ServerSideSessionBackend, ServerSideSessionConfig
from litestar.security.session_auth import SessionAuth


class User(BaseModel):
    id: UUID
    name: str
    email: EmailStr


session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    # we must pass a config for a session backend.
    # all session backends are supported
    session_backend_config=ServerSideSessionConfig(),
    # exclude any URLs that should not have authentication.
    # We exclude the documentation URLs, signup and login.
    exclude=["/login", "/signup", "/schema"],
)
