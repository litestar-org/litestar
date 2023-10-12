from __future__ import annotations

import contextlib
import importlib
import inspect
import sys
from dataclasses import dataclass
from functools import wraps
from itertools import chain
from os import getenv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Generator, Iterable, Sequence, TypeVar, cast

from rich import get_console
from rich.table import Table
from typing_extensions import ParamSpec, get_type_hints

from litestar import Litestar, __version__
from litestar.middleware import DefineMiddleware
from litestar.utils import get_name

RICH_CLICK_INSTALLED = False
with contextlib.suppress(ImportError):
    import rich_click  # noqa: F401

    RICH_CLICK_INSTALLED = True
UVICORN_INSTALLED = False
with contextlib.suppress(ImportError):
    import uvicorn  # noqa: F401

    UVICORN_INSTALLED = True
JSBEAUTIFIER_INSTALLED = False
with contextlib.suppress(ImportError):
    import jsbeautifier  # noqa: F401

    JSBEAUTIFIER_INSTALLED = True
if TYPE_CHECKING or not RICH_CLICK_INSTALLED:  # pragma: no cover
    from click import ClickException, Command, Context, Group, pass_context
else:
    from rich_click import ClickException, Context, pass_context
    from rich_click.rich_command import RichCommand as Command  # noqa: TCH002
    from rich_click.rich_group import RichGroup as Group


__all__ = (
    "RICH_CLICK_INSTALLED",
    "UVICORN_INSTALLED",
    "JSBEAUTIFIER_INSTALLED",
    "LoadedApp",
    "LitestarCLIException",
    "LitestarEnv",
    "LitestarExtensionGroup",
    "LitestarGroup",
    "show_app_info",
)


if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points  # pragma: no cover


if TYPE_CHECKING:
    from litestar.types import AnyCallable


P = ParamSpec("P")
T = TypeVar("T")


AUTODISCOVERY_FILE_NAMES = ["app", "application"]

console = get_console()


class LitestarCLIException(ClickException):
    """Base class for Litestar CLI exceptions."""

    def __init__(self, message: str) -> None:
        """Initialize exception and style error message."""
        super().__init__(message)


@dataclass
class LitestarEnv:
    """Information about the current Litestar environment variables."""

    app_path: str
    debug: bool
    app: Litestar
    cwd: Path
    host: str | None = None
    port: int | None = None
    fd: int | None = None
    uds: str | None = None
    reload: bool | None = None
    reload_dirs: tuple[str, ...] | None = None
    web_concurrency: int | None = None
    is_app_factory: bool = False

    @classmethod
    def from_env(cls, app_path: str | None, app_dir: Path | None = None) -> LitestarEnv:
        """Load environment variables.

        If ``python-dotenv`` is installed, use it to populate environment first
        """
        cwd = Path().cwd() if app_dir is None else app_dir
        cwd_str_path = str(cwd)
        if cwd_str_path not in sys.path:
            sys.path.append(cwd_str_path)

        with contextlib.suppress(ImportError):
            import dotenv

            dotenv.load_dotenv()
        app_path = app_path or getenv("LITESTAR_APP")
        if app_path:
            console.print(f"Using Litestar app from env: [bright_blue]{app_path!r}")
            loaded_app = _load_app_from_path(app_path)
        else:
            loaded_app = _autodiscover_app(cwd)

        port = getenv("LITESTAR_PORT")
        web_concurrency = getenv("WEB_CONCURRENCY")
        uds = getenv("LITESTAR_UNIX_DOMAIN_SOCKET")
        fd = getenv("LITESTAR_FILE_DESCRIPTOR")
        reload_dirs = tuple(s.strip() for s in getenv("LITESTAR_RELOAD_DIRS", "").split(",") if s) or None

        return cls(
            app_path=loaded_app.app_path,
            app=loaded_app.app,
            debug=_bool_from_env("LITESTAR_DEBUG"),
            host=getenv("LITESTAR_HOST"),
            port=int(port) if port else None,
            uds=uds,
            fd=int(fd) if fd else None,
            reload=_bool_from_env("LITESTAR_RELOAD"),
            reload_dirs=reload_dirs,
            web_concurrency=int(web_concurrency) if web_concurrency else None,
            is_app_factory=loaded_app.is_factory,
            cwd=cwd,
        )


@dataclass
class LoadedApp:
    """Information about a loaded Litestar app."""

    app: Litestar
    app_path: str
    is_factory: bool


class LitestarGroup(Group):
    """:class:`click.Group` subclass that automatically injects ``app`` and ``env` kwargs into commands that request it.

    Use this as the ``cls`` for :class:`click.Group` if you're extending the internal CLI with a group. For ``command``s
    added directly to the root group this is not needed.
    """

    def __init__(
        self,
        name: str | None = None,
        commands: dict[str, Command] | Sequence[Command] | None = None,
        **attrs: Any,
    ) -> None:
        """Init ``LitestarGroup``"""
        self.group_class = LitestarGroup
        super().__init__(name=name, commands=commands, **attrs)

    def add_command(self, cmd: Command, name: str | None = None) -> None:
        """Add command.

        If necessary, inject ``app`` and ``env`` kwargs
        """
        if cmd.callback:
            cmd.callback = _inject_args(cmd.callback)
        super().add_command(cmd)

    def command(self, *args: Any, **kwargs: Any) -> Callable[[AnyCallable], Command] | Command:  # type: ignore[override]
        # For some reason, even when copying the overloads + signature from click 1:1, mypy goes haywire
        """Add a function as a command.

        If necessary, inject ``app`` and ``env`` kwargs
        """

        def decorator(f: AnyCallable) -> Command:
            f = _inject_args(f)
            return cast("Command", Group.command(self, *args, **kwargs)(f))

        return decorator


class LitestarExtensionGroup(LitestarGroup):
    """``LitestarGroup`` subclass that will load Litestar-CLI extensions from the `litestar.commands` entry_point.

    This group class should not be used on any group besides the root ``litestar_group``.
    """

    def __init__(
        self,
        name: str | None = None,
        commands: dict[str, Command] | Sequence[Command] | None = None,
        **attrs: Any,
    ) -> None:
        """Init ``LitestarExtensionGroup``"""
        super().__init__(name=name, commands=commands, **attrs)
        self._prepare_done = False

        for entry_point in entry_points(group="litestar.commands"):
            command = entry_point.load()
            _wrap_commands([command])
            self.add_command(command, entry_point.name)

    def _prepare(self, ctx: Context) -> None:
        if self._prepare_done:
            return

        if isinstance(ctx.obj, LitestarEnv):
            env: LitestarEnv | None = ctx.obj
        else:
            try:
                env = ctx.obj = LitestarEnv.from_env(ctx.params.get("app_path"), ctx.params.get("app_dir"))
            except LitestarCLIException:
                env = None

        if env:
            for plugin in env.app.plugins.cli:
                plugin.on_cli_init(self)

        self._prepare_done = True

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: Context | None = None,
        **extra: Any,
    ) -> Context:
        ctx = super().make_context(info_name, args, parent, **extra)
        self._prepare(ctx)
        return ctx

    def list_commands(self, ctx: Context) -> list[str]:
        self._prepare(ctx)
        return super().list_commands(ctx)


def _inject_args(func: Callable[P, T]) -> Callable[P, T]:
    """Inject the app instance into a ``Command``"""
    params = inspect.signature(func).parameters

    @wraps(func)
    def wrapped(ctx: Context, /, *args: P.args, **kwargs: P.kwargs) -> T:
        needs_app = "app" in params
        needs_env = "env" in params
        if needs_env or needs_app:
            # only resolve this if actually requested. Commands that don't need an env or app should be able to run
            # without
            if not isinstance(ctx.obj, LitestarEnv):
                ctx.obj = ctx.obj()
            env = ctx.ensure_object(LitestarEnv)
            if needs_app:
                kwargs["app"] = env.app
            if needs_env:
                kwargs["env"] = env

        if "ctx" in params:
            kwargs["ctx"] = ctx

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
    if not isinstance(app, Litestar) and callable(app):
        app = app()
        is_factory = True
    return LoadedApp(app=app, app_path=app_path, is_factory=is_factory)


def _path_to_dotted_path(path: Path) -> str:
    if path.stem == "__init__":
        path = path.parent
    return ".".join(path.with_suffix("").parts)


def _arbitrary_autodiscovery_paths(base_dir: Path) -> Generator[Path, None, None]:
    yield from _autodiscovery_paths(base_dir, arbitrary=False)
    for path in base_dir.iterdir():
        if path.name.startswith(".") or path.name.startswith("_"):
            continue
        if path.is_file() and path.suffix == ".py":
            yield path


def _autodiscovery_paths(base_dir: Path, arbitrary: bool = True) -> Generator[Path, None, None]:
    for name in AUTODISCOVERY_FILE_NAMES:
        path = base_dir / name

        if path.exists() or path.with_suffix(".py").exists():
            yield path
        if arbitrary and path.is_dir():
            yield from _arbitrary_autodiscovery_paths(path)


def _autodiscover_app(cwd: Path) -> LoadedApp:
    for file_path in _autodiscovery_paths(cwd):
        import_path = _path_to_dotted_path(file_path.relative_to(cwd))
        module = importlib.import_module(import_path)

        for attr, value in chain(
            [("app", getattr(module, "app", None)), ("application", getattr(module, "application", None))],
            module.__dict__.items(),
        ):
            if isinstance(value, Litestar):
                app_string = f"{import_path}:{attr}"
                console.print(f"Using Litestar app from [bright_blue]{app_string}")
                return LoadedApp(app=value, app_path=app_string, is_factory=False)

        if hasattr(module, "create_app"):
            app_string = f"{import_path}:create_app"
            console.print(f"Using Litestar factory [bright_blue]{app_string}")
            return LoadedApp(app=module.create_app(), app_path=app_string, is_factory=True)

        for attr, value in module.__dict__.items():
            if not callable(value):
                continue
            return_annotation = (
                get_type_hints(value, include_extras=True).get("return") if hasattr(value, "__annotations__") else None
            )
            if not return_annotation:
                continue
            if return_annotation in ("Litestar", Litestar):
                app_string = f"{import_path}:{attr}"
                console.print(f"Using Litestar factory [bright_blue]{app_string}")
                return LoadedApp(app=value(), app_path=f"{app_string}", is_factory=True)

    raise LitestarCLIException("Could not find a Litestar app or factory")


def _format_is_enabled(value: Any) -> str:
    """Return a coloured string `"Enabled" if ``value`` is truthy, else "Disabled"."""
    return "[green]Enabled[/]" if value else "[red]Disabled[/]"


def show_app_info(app: Litestar) -> None:  # pragma: no cover
    """Display basic information about the application and its configuration."""

    table = Table(show_header=False)
    table.add_column("title", style="cyan")
    table.add_column("value", style="bright_blue")

    table.add_row("Litestar version", f"{__version__.major}.{__version__.minor}.{__version__.patch}")
    table.add_row("Debug mode", _format_is_enabled(app.debug))
    table.add_row("Python Debugger on exception", _format_is_enabled(app.pdb_on_exception))
    table.add_row("CORS", _format_is_enabled(app.cors_config))
    table.add_row("CSRF", _format_is_enabled(app.csrf_config))
    if app.allowed_hosts:
        allowed_hosts = app.allowed_hosts

        table.add_row("Allowed hosts", ", ".join(allowed_hosts.allowed_hosts))

    openapi_enabled = _format_is_enabled(app.openapi_config)
    if app.openapi_config:
        openapi_enabled += f" path=[yellow]{app.openapi_config.openapi_controller.path}"
    table.add_row("OpenAPI", openapi_enabled)

    table.add_row("Compression", app.compression_config.backend if app.compression_config else "[red]Disabled")

    if app.template_engine:
        table.add_row("Template engine", type(app.template_engine).__name__)

    if app.static_files_config:
        static_files_configs = app.static_files_config
        static_files_info = [
            f"path=[yellow]{static_files.path}[/] dirs=[yellow]{', '.join(map(str, static_files.directories))}[/] "
            f"html_mode={_format_is_enabled(static_files.html_mode)}"
            for static_files in static_files_configs
        ]
        table.add_row("Static files", "\n".join(static_files_info))

    middlewares = []
    for middleware in app.middleware:
        updated_middleware = middleware.middleware if isinstance(middleware, DefineMiddleware) else middleware
        middlewares.append(get_name(updated_middleware))
    if middlewares:
        table.add_row("Middlewares", ", ".join(middlewares))

    console.print(table)
