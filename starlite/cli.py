from __future__ import annotations

import importlib
import inspect
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, Any

import rich
import rich.tree
from click import ClickException, argument, confirm, group, option, style
from rich.console import Console
from rich.table import Table

from starlite import DefineMiddleware, HTTPRoute, Starlite, WebSocketRoute
from starlite.utils import is_class_and_subclass
from starlite.utils.helpers import get_name, unwrap_partial

if TYPE_CHECKING:
    from starlite.middleware.session.base import ServerSideBackend

console = Console()


class _StarliteCLIException(ClickException):
    def __init__(self, message: str) -> None:
        super().__init__(style(message, fg="red"))


def _autodiscover_app() -> tuple[str, Starlite]:
    if app_path := getenv("STARLITE_APP"):
        console.print(f"Using starlite app from env: [bright_blue]{app_path!r}")
        module_path, app_name = app_path.split(":")
        module = importlib.import_module(module_path)
        return app_path, getattr(module, app_name)

    cwd = Path().cwd()
    for name in ["asgi.py", "app.py", "application.py"]:
        path = cwd / name
        if not path.exists():
            continue

        module = importlib.import_module(path.stem)
        for attr, value in module.__dict__.items():
            if isinstance(value, Starlite):
                app_string = f"{path.stem}:{attr}"
                console.print(f"Using Starlite app from [bright_blue]{path}:{attr}")
                return app_string, value

    raise _StarliteCLIException("Could not find a Starlite app")


def _get_app() -> Starlite:
    return _autodiscover_app()[1]


def _bool_enabled(value: Any) -> str:
    if value:
        return "[green]Enabled[/]"
    return "[red]Disabled[/]"


def _show_app_info(app: Starlite) -> None:
    table = Table(show_header=False)
    table.add_column("title", style="cyan")
    table.add_column("value", style="bright_blue")

    table.add_row("Debug mode", _bool_enabled(app.debug))
    table.add_row("CORS", _bool_enabled(app.cors_config))
    table.add_row("CSRF", _bool_enabled(app.csrf_config))
    if app.allowed_hosts:
        allowed_hosts = app.allowed_hosts

        table.add_row("Allowed hosts", ", ".join(allowed_hosts.allowed_hosts))

    table.add_row("Request caching", _bool_enabled(app.cache))
    table.add_row("OpenAPI", _bool_enabled(app.openapi_config))

    table.add_row("Compression", app.compression_config.backend if app.compression_config else "[red]Disabled")

    if app.template_engine:
        table.add_row("Template engine", type(app.template_engine).__name__)

    if app.static_files_config:
        static_files_configs = app.static_files_config
        if not isinstance(static_files_configs, list):
            static_files_configs = [static_files_configs]
        static_files_info = []
        for static_files in static_files_configs:
            static_files_info.append(
                f"path=[yellow]{static_files.path}[/] dirs=[yellow]{', '.join(map(str, static_files.directories))}[/] "
                f"html_mode={_bool_enabled(static_files.html_mode)}",
            )
        table.add_row("Static files", "\n".join(static_files_info))

    if app.plugins:
        plugin_names = [type(plugin).__name__ for plugin in app.plugins]
        table.add_row("Plugins", ", ".join(plugin_names))

    middlewares = []
    for middleware in app.middleware:
        if isinstance(middleware, DefineMiddleware):
            middleware = middleware.middleware
        middlewares.append(get_name(middleware))
    if middlewares:
        table.add_row("Middlewares", ", ".join(middlewares))

    console.print(table)


@group()
def cli() -> None:
    """Starlite CLI."""


@cli.command(name="info")
def info_command() -> None:
    """Show information about the detected Starlite app."""
    _show_app_info(_get_app())


@cli.command()
@option("-r", "--reload", help="Reload server on changes", default=False)
@option("-p", "--port", help="Serve under this port", type=int, default=8000)
@option("--host", help="Server under this host", default="127.0.0.1")
def run(reload: bool, port: int, host: str) -> None:
    """Run a Starlite app.

    The app can be specified in the STARLITE_APP environment variable, or an asgi.py, app.py or application.py file.
    """
    try:
        import uvicorn
    except ImportError:
        raise _StarliteCLIException("Uvicorn needs to be installed to run an app")  # pylint: disable=W0707

    app_path, app = _autodiscover_app()
    _show_app_info(app)

    console.rule("[yellow]Starting server process", align="left")

    uvicorn.run(app_path, reload=reload, host=host, port=port)


@cli.command()
def routes() -> None:
    """Display information about the application's routes."""
    app = _get_app()
    tree = rich.tree.Tree("", hide_root=True)

    for route in sorted(app.routes, key=lambda r: r.path):
        if isinstance(route, HTTPRoute):
            branch = tree.add(f"[green]{route.path}[/green] (HTTP)")
            for handler in route.route_handlers:
                handler_info = [
                    f"[blue]{handler.name or handler.handler_name}[/blue]",
                ]

                if inspect.iscoroutinefunction(unwrap_partial(handler.fn.value)):
                    handler_info.append("[magenta]async[/magenta]")
                else:
                    handler_info.append("[yellow]sync[/yellow]")

                handler_info.append(f'[cyan]{", ".join(sorted(handler.http_methods))}[/cyan]')

                if len(handler.paths) > 1:
                    for path in handler.paths:
                        branch.add(" ".join([f"[green]{path}[green]", *handler_info]))
                else:
                    branch.add(" ".join(handler_info))

        else:
            if isinstance(route, WebSocketRoute):
                route_type = "WS"
            else:
                route_type = "ASGI"
            branch = tree.add(f"[green]{route.path}[/green] ({route_type})")
            branch.add(f"[blue]{route.route_handler.name or route.route_handler.handler_name}[/blue]")

    console.print(tree)


def _get_session_backend() -> ServerSideBackend:
    from starlite.middleware.session.base import ServerSideBackend, SessionMiddleware

    app = _get_app()
    for middleware in app.middleware:
        if isinstance(middleware, DefineMiddleware):
            if not is_class_and_subclass(middleware.middleware, SessionMiddleware):
                continue
            backend = middleware.kwargs["backend"]
            if not isinstance(backend, ServerSideBackend):
                raise _StarliteCLIException("Only server-side backends are supported")
            return backend
    raise _StarliteCLIException("Session middleware not installed")


@cli.group()
def sessions() -> None:
    """Manage server-side sessions."""


@sessions.command("sessions")
@argument("session-id")
def delete_session(session_id: str) -> None:
    """Delete a specific session."""
    import anyio

    backend = _get_session_backend()
    if not anyio.run(backend.get, session_id):
        console.print(f"[red]Session {session_id!r} not found")
        return

    if confirm(style(f"Delete session {session_id!r}?", fg="red"), abort=True):
        anyio.run(backend.delete, session_id)
        console.print(f"[green]Deleted session {session_id!r}")


@sessions.command("clear")
def clear_sessions() -> None:
    """Delete all sessions."""
    import anyio

    backend = _get_session_backend()

    if confirm(style("Delete all active sessions?", fg="red"), abort=True):
        anyio.run(backend.delete_all)
        console.print("[green]All active sessions deleted")
