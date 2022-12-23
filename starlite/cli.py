import importlib
import inspect
import sys
from dataclasses import dataclass
from functools import wraps
from importlib.metadata import version
from os import getenv
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from click import (
    ClickException,
    Command,
    Context,
    Group,
    argument,
    group,
    option,
    pass_context,
    style,
)
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree
from typing_extensions import Concatenate, ParamSpec

from starlite import DefineMiddleware, HTTPRoute, Starlite, WebSocketRoute
from starlite.middleware.session import SessionMiddleware
from starlite.middleware.session.base import ServerSideBackend
from starlite.utils import get_name, is_class_and_subclass
from starlite.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from starlite.types import AnyCallable

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points


P = ParamSpec("P")
T = TypeVar("T")
console = Console()


AUTODISCOVER_PATHS = [
    "asgi.py",
    "app.py",
    "application.py",
    "app/__init__.py",
    "application/__init__.py",
]


class StarliteCLIException(ClickException):
    """Base class for Starlite CLI exceptions."""

    def __init__(self, message: str) -> None:
        """Initialize exception and style error message."""
        super().__init__(style(message, fg="red"))


@dataclass
class StarliteEnv:
    """Information about the current Starlite environment variables."""

    app_path: str
    debug: bool
    app: Starlite
    host: Optional[str] = None
    port: Optional[int] = None
    reload: Optional[bool] = None

    @classmethod
    def from_env(cls, app_path: Optional[str]) -> "StarliteEnv":
        """Load environment variables.

        If `python-dotenv` is installed, use it to populate environment first
        """
        try:
            import dotenv

            dotenv.load_dotenv()
        except ImportError:
            pass

        if not app_path:
            app_path, app = _autodiscover_app(getenv("STARLITE_APP"))
        else:
            app = _load_app_from_path(app_path)

        port = getenv("STARLITE_PORT")

        return cls(
            app_path=app_path,
            app=app,
            debug=_bool_from_env("STARLITE_DEBUG"),
            host=getenv("STARLITE_HOST"),
            port=int(port) if port else None,
            reload=_bool_from_env("STARLITE_RELOAD"),
        )


class StarliteGroup(Group):
    """`click.Group` subclass that automatically injects `app` and `env` kwargs into commands that request it."""

    def __init__(
        self,
        name: Optional[str] = None,
        commands: Optional[Union[Dict[str, Command], Sequence[Command]]] = None,
        **attrs: Any,
    ):
        """Init `StarliteGroup`"""
        self.group_class = StarliteGroup
        super().__init__(name=name, commands=commands, **attrs)

    def add_command(self, cmd: Command, name: Optional[str] = None) -> None:
        """Add command.

        If necessary, inject `app` and `env` kwargs
        """
        if cmd.callback:
            cmd.callback = _inject_args(cmd.callback)
        super().add_command(cmd)

    def command(self, *args: Any, **kwargs: Any) -> Union[Callable[["AnyCallable"], Command], Command]:  # type: ignore[override]
        # For some reason, even when copying the overloads + signature from click 1:1, mypy goes haywire
        """Add a function as a command.

        If necessary, inject `app` and `env` kwargs
        """

        def decorator(f: "AnyCallable") -> Command:
            f = _inject_args(f)
            return cast("Command", Group.command(self, *args, **kwargs)(f))  # pylint: disable=E1102

        return decorator


class StarliteExtensionGroup(StarliteGroup):
    """`StarliteGroup` subclass that will load Starlite-CLI extensions from the `starlite.commands` entry_point."""

    def __init__(
        self,
        name: Optional[str] = None,
        commands: Optional[Union[Dict[str, Command], Sequence[Command]]] = None,
        **attrs: Any,
    ):
        """Init `StarliteExtensionGroup`"""
        super().__init__(name=name, commands=commands, **attrs)

        for entry_point in entry_points(group="starlite.commands"):
            command = entry_point.load()
            _wrap_commands([command])
            self.add_command(command, entry_point.name)


def _bool_from_env(key: str, default: bool = False) -> bool:
    value = getenv(key)
    if not value:
        return default
    value = value.lower()
    return value in ("true", "1")


def _load_app_from_path(app_path: str) -> Starlite:
    module_path, app_name = app_path.split(":")
    module = importlib.import_module(module_path)
    return cast("Starlite", getattr(module, app_name))


def _path_to_dotted_path(path: Path) -> str:
    if path.stem == "__init__":
        path = path.parent
    return ".".join(path.with_suffix("").parts)


def _autodiscover_app(app_path: Optional[str]) -> Tuple[str, Starlite]:
    if app_path:
        console.print(f"Using Starlite app from env: [bright_blue]{app_path!r}")
        return app_path, _load_app_from_path(app_path)

    cwd = Path().cwd()
    for name in AUTODISCOVER_PATHS:
        path = cwd / name
        if not path.exists():
            continue

        dotted_path = _path_to_dotted_path(path.relative_to(cwd))
        module = importlib.import_module(dotted_path)
        for attr, value in module.__dict__.items():
            if isinstance(value, Starlite):
                app_string = f"{dotted_path}:{attr}"
                console.print(f"Using Starlite app from [bright_blue]{path}:{attr}")
                return app_string, value
    raise StarliteCLIException("Could not find a Starlite app")


def _inject_args(func: Callable[P, T]) -> Callable[Concatenate[Context, P], T]:
    """Inject the app instance into a `Command`"""
    params = inspect.signature(func).parameters

    @wraps(func)
    def wrapped(ctx: Context, /, *args: P.args, **kwargs: P.kwargs) -> T:
        env = ctx.ensure_object(StarliteEnv)
        if "app" in params:
            kwargs["app"] = env.app
        if "env" in params:
            kwargs["env"] = env
        return func(*args, **kwargs)

    return pass_context(wrapped)


def _wrap_commands(commands: Iterable[Command]) -> None:
    for command in commands:
        if isinstance(command, Group):
            _wrap_commands(command.commands.values())
        elif command.callback:
            command.callback = _inject_args(command.callback)


def _format_is_enabled(value: Any) -> str:
    """Return a coloured string `"Enabled" if `value` is truthy, else "Disabled"."""
    if value:
        return "[green]Enabled[/]"
    return "[red]Disabled[/]"


def _get_session_backend(app: Starlite) -> ServerSideBackend:
    for middleware in app.middleware:
        if isinstance(middleware, DefineMiddleware):
            if not is_class_and_subclass(middleware.middleware, SessionMiddleware):
                continue
            backend = middleware.kwargs["backend"]
            if not isinstance(backend, ServerSideBackend):
                raise StarliteCLIException("Only server-side backends are supported")
            return backend
    raise StarliteCLIException("Session middleware not installed")


def _show_app_info(app: Starlite) -> None:  # pragma: no cover
    """Display basic information about the application and its configuration."""

    table = Table(show_header=False)
    table.add_column("title", style="cyan")
    table.add_column("value", style="bright_blue")

    table.add_row("Starlite version", version("starlite"))
    table.add_row("Debug mode", _format_is_enabled(app.debug))
    table.add_row("CORS", _format_is_enabled(app.cors_config))
    table.add_row("CSRF", _format_is_enabled(app.csrf_config))
    if app.allowed_hosts:
        allowed_hosts = app.allowed_hosts

        table.add_row("Allowed hosts", ", ".join(allowed_hosts.allowed_hosts))

    table.add_row("Request caching", _format_is_enabled(app.cache))
    openapi_enabled = _format_is_enabled(app.openapi_config)
    if app.openapi_config:
        openapi_enabled += f" path=[yellow]{app.openapi_config.openapi_controller.path}"
    table.add_row("OpenAPI", openapi_enabled)

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
                f"html_mode={_format_is_enabled(static_files.html_mode)}",
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


@group(cls=StarliteExtensionGroup)
@option("--app", "app_path", help="Module path to a Starlite application")
@pass_context
def cli(ctx: Context, app_path: Optional[str]) -> None:
    """Starlite CLI."""

    # _wrap_commands(cli.commands.values())
    ctx.obj = StarliteEnv.from_env(app_path)


@cli.command(name="info")
def info_command(app: Starlite) -> None:
    """Show information about the detected Starlite app."""

    _show_app_info(app)


@cli.command()
@option("-r", "--reload", help="Reload server on changes", default=False, is_flag=True)
@option("-p", "--port", help="Serve under this port", type=int, default=8000, show_default=True)
@option("--host", help="Server under this host", default="127.0.0.1", show_default=True)
@option("--debug", help="Run app in debug mode", is_flag=True)
def run(
    reload: bool,
    port: int,
    host: str,
    debug: bool,
    env: StarliteEnv,
    app: Starlite,
) -> None:
    """Run a Starlite app.

    The app can be either passed as a module path in the form of <module name>.<submodule>:<app instance>, set as an
    environment variable STARLITE_APP with the same format or automatically discovered from one of these canonical
    paths: app.py, asgi.py, application.py or app/__init__.py
    """

    try:
        import uvicorn
    except ImportError:
        raise StarliteCLIException("Uvicorn needs to be installed to run an app")  # pylint: disable=W0707

    if debug or env.debug:
        app.debug = True

    _show_app_info(app)

    console.rule("[yellow]Starting server process", align="left")

    uvicorn.run(
        env.app_path,
        reload=env.reload or reload,
        host=env.host or host,
        port=env.port or port,
    )


@cli.command()
def routes(app: Starlite) -> None:  # pragma: no cover
    """Display information about the application's routes."""

    tree = Tree("", hide_root=True)

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


@cli.group()
def sessions() -> None:
    """Manage server-side sessions."""


@sessions.command("delete")
@argument("session-id")
def delete_session(session_id: str, app: Starlite) -> None:
    """Delete a specific session."""
    import anyio

    backend = _get_session_backend(app)

    if Confirm.ask(f"Delete session {session_id!r}?"):
        anyio.run(backend.delete, session_id)
        console.print(f"[green]Deleted session {session_id!r}")


@sessions.command("clear")
def clear_sessions(app: Starlite) -> None:
    """Delete all sessions."""
    import anyio

    backend = _get_session_backend(app)

    if Confirm.ask("[red]Delete all sessions?"):
        anyio.run(backend.delete_all)
        console.print("[green]All active sessions deleted")
