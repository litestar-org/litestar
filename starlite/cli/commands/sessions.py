from click import argument, group
from rich.prompt import Confirm

from starlite import Starlite
from starlite.cli._utils import StarliteCLIException, StarliteGroup, console
from starlite.middleware import DefineMiddleware
from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.server_side import ServerSideSessionBackend
from starlite.utils import is_class_and_subclass

__all__ = ("clear_sessions_command", "delete_session_command", "get_session_backend", "sessions_group")


def get_session_backend(app: Starlite) -> ServerSideSessionBackend:
    """Get the session backend used by a ``Starlite`` app."""
    for middleware in app.middleware:
        if isinstance(middleware, DefineMiddleware):
            if not is_class_and_subclass(middleware.middleware, SessionMiddleware):
                continue
            backend = middleware.kwargs["backend"]
            if not isinstance(backend, ServerSideSessionBackend):
                raise StarliteCLIException("Only server-side backends are supported")
            return backend
    raise StarliteCLIException("Session middleware not installed")


@group(cls=StarliteGroup, name="sessions")
def sessions_group() -> None:
    """Manage server-side sessions."""


@sessions_group.command("delete")
@argument("session-id")
def delete_session_command(session_id: str, app: Starlite) -> None:
    """Delete a specific session."""
    import anyio

    backend = get_session_backend(app)
    store = backend.config.get_store_from_app(app)

    if Confirm.ask(f"Delete session {session_id!r}?"):
        anyio.run(backend.delete, session_id, store)
        console.print(f"[green]Deleted session {session_id!r}")


@sessions_group.command("clear")
def clear_sessions_command(app: Starlite) -> None:
    """Delete all sessions."""
    import anyio

    backend = get_session_backend(app)
    store = backend.config.get_store_from_app(app)
    if not hasattr(store, "delete_all"):
        raise StarliteCLIException(f"{type(store)} does not support clearing all sessions")

    if Confirm.ask("[red]Delete all sessions?"):
        anyio.run(store.delete_all)  # pyright: ignore
        console.print("[green]All active sessions deleted")
