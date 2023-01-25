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
    TypeVar,
    Union,
    cast,
)

from click import ClickException, Command, Context, Group, pass_context, style
from rich.console import Console
from rich.table import Table
from typing_extensions import Concatenate, ParamSpec

from starlite import DefineMiddleware, Starlite
from starlite.utils import get_name

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points  # pragma: no cover


if TYPE_CHECKING:
    from starlite.types import AnyCallable


P = ParamSpec("P")
T = TypeVar("T")


AUTODISCOVER_PATHS = [
    "asgi.py",
    "app.py",
    "application.py",
    "app/__init__.py",
    "application/__init__.py",
]

console = Console()


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
    cwd: Path
    host: Optional[str] = None
    port: Optional[int] = None
    reload: Optional[bool] = None
    is_app_factory: bool = False

    @classmethod
    def from_env(cls, app_path: Optional[str]) -> "StarliteEnv":
        """Load environment variables.

        If ``python-dotenv`` is installed, use it to populate environment first
        """
        cwd = Path().cwd()
        cwd_str_path = str(cwd)
        if cwd_str_path not in sys.path:
            sys.path.append(cwd_str_path)

        try:
            import dotenv

            dotenv.load_dotenv()
        except ImportError:
            pass

        if not app_path:
            loaded_app = _autodiscover_app(getenv("STARLITE_APP"), cwd)
        else:
            loaded_app = _load_app_from_path(app_path)

        port = getenv("STARLITE_PORT")

        return cls(
            app_path=loaded_app.app_path,
            app=loaded_app.app,
            debug=_bool_from_env("STARLITE_DEBUG"),
            host=getenv("STARLITE_HOST"),
            port=int(port) if port else None,
            reload=_bool_from_env("STARLITE_RELOAD"),
            is_app_factory=loaded_app.is_factory,
            cwd=cwd,
        )


@dataclass
class LoadedApp:
    """Information about a loaded Starlite app."""

    app: Starlite
    app_path: str
    is_factory: bool


class StarliteGroup(Group):
    """:class:`click.Group` subclass that automatically injects ``app`` and ``env` kwargs into commands that request it.

    Use this as the ``cls`` for :class:`click.Group` if you're extending the internal CLI with a group. For ``command``s
    added directly to the root group this is not needed.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        commands: Optional[Union[Dict[str, Command], Sequence[Command]]] = None,
        **attrs: Any,
    ):
        """Init ``StarliteGroup``"""
        self.group_class = StarliteGroup
        super().__init__(name=name, commands=commands, **attrs)

    def add_command(self, cmd: Command, name: Optional[str] = None) -> None:
        """Add command.

        If necessary, inject ``app`` and ``env`` kwargs
        """
        if cmd.callback:
            cmd.callback = _inject_args(cmd.callback)
        super().add_command(cmd)

    def command(self, *args: Any, **kwargs: Any) -> Union[Callable[["AnyCallable"], Command], Command]:  # type: ignore[override]
        # For some reason, even when copying the overloads + signature from click 1:1, mypy goes haywire
        """Add a function as a command.

        If necessary, inject ``app`` and ``env`` kwargs
        """

        def decorator(f: "AnyCallable") -> Command:
            f = _inject_args(f)
            return cast("Command", Group.command(self, *args, **kwargs)(f))  # pylint: disable=E1102

        return decorator


class StarliteExtensionGroup(StarliteGroup):
    """``StarliteGroup`` subclass that will load Starlite-CLI extensions from the `starlite.commands` entry_point.

    This group class should not be used on any group besides the root ``starlite_group``.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        commands: Optional[Union[Dict[str, Command], Sequence[Command]]] = None,
        **attrs: Any,
    ):
        """Init ``StarliteExtensionGroup``"""
        super().__init__(name=name, commands=commands, **attrs)

        for entry_point in entry_points(group="starlite.commands"):
            command = entry_point.load()
            _wrap_commands([command])
            self.add_command(command, entry_point.name)


def _inject_args(func: Callable[P, T]) -> Callable[Concatenate[Context, P], T]:
    """Inject the app instance into a ``Command``"""
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


def _bool_from_env(key: str, default: bool = False) -> bool:
    value = getenv(key)
    if not value:
        return default
    value = value.lower()
    return value in ("true", "1")


def _load_app_from_path(app_path: str) -> LoadedApp:
    module_path, app_name = app_path.split(":")
    module = importlib.import_module(module_path)
    app = getattr(module, app_name)
    is_factory = False
    if not isinstance(app, Starlite) and callable(app):
        app = app()
        is_factory = True
    return LoadedApp(app=app, app_path=app_path, is_factory=is_factory)


def _path_to_dotted_path(path: Path) -> str:
    if path.stem == "__init__":
        path = path.parent
    return ".".join(path.with_suffix("").parts)


def _autodiscover_app(app_path: Optional[str], cwd: Path) -> LoadedApp:
    if app_path:
        console.print(f"Using Starlite app from env: [bright_blue]{app_path!r}")
        return _load_app_from_path(app_path)

    for name in AUTODISCOVER_PATHS:
        path = cwd / name
        if not path.exists():
            continue

        dotted_path = _path_to_dotted_path(path.relative_to(cwd))
        module = importlib.import_module(dotted_path)

        for attr, value in module.__dict__.items():
            if isinstance(value, Starlite):
                app_string = f"{dotted_path}:{attr}"
                console.print(f"Using Starlite app from [bright_blue]{app_string}")
                return LoadedApp(app=value, app_path=app_string, is_factory=False)

        if hasattr(module, "create_app"):
            app_string = f"{dotted_path}:create_app"
            console.print(f"Using Starlite factory [bright_blue]{app_string}")
            return LoadedApp(app=module.create_app(), app_path=app_string, is_factory=True)

        for attr, value in module.__dict__.items():
            if not callable(value):
                continue
            signature = inspect.signature(value)
            if signature.return_annotation in ("Starlite", Starlite):
                app_string = f"{dotted_path}:{attr}"
                console.print(f"Using Starlite factory [bright_blue]{app_string}")
                return LoadedApp(app=value(), app_path=f"{app_string}", is_factory=True)

    raise StarliteCLIException("Could not find a Starlite app or factory")


def _format_is_enabled(value: Any) -> str:
    """Return a coloured string `"Enabled" if ``value`` is truthy, else "Disabled"."""
    if value:
        return "[green]Enabled[/]"
    return "[red]Disabled[/]"


def show_app_info(app: Starlite) -> None:  # pragma: no cover
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
