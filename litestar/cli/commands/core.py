from __future__ import annotations

import inspect
import multiprocessing
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any

import uvicorn
from rich.tree import Tree

from litestar.cli._utils import RICH_CLICK_INSTALLED, LitestarEnv, console, show_app_info
from litestar.routes import HTTPRoute, WebSocketRoute
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING or not RICH_CLICK_INSTALLED:  # pragma: no cover
    import click
    from click import Context, command, option
else:
    import rich_click as click
    from rich_click import Context, command, option

__all__ = ("info_command", "routes_command", "run_command")

if TYPE_CHECKING:
    from litestar import Litestar


def _convert_uvicorn_args(args: dict[str, Any]) -> list[str]:
    process_args = []
    for arg, value in args.items():
        if isinstance(value, bool):
            if value:
                process_args.append(f"--{arg}")
        elif isinstance(value, tuple):
            process_args.extend(f"--{arg}={item}" for item in value)
        else:
            process_args.append(f"--{arg}={value}")

    return process_args


@command(name="version")
@option("-s", "--short", help="Exclude release level and serial information", is_flag=True, default=False)
def version_command(short: bool) -> None:
    """Show the currently installed Litestar version."""
    from litestar import __version__

    click.echo(__version__.formatted(short=short))


@command(name="info")
def info_command(app: Litestar) -> None:
    """Show information about the detected Litestar app."""

    show_app_info(app)


@command(name="run")
@option("-r", "--reload", help="Reload server on changes", default=False, is_flag=True)
@option("-R", "--reload-dir", help="Directories to watch for file changes", multiple=True)
@option("-p", "--port", help="Serve under this port", type=int, default=8000, show_default=True)
@option(
    "-W",
    "--wc",
    "--web-concurrency",
    help="The number of HTTP workers to launch",
    type=click.IntRange(min=1, max=multiprocessing.cpu_count() + 1),
    show_default=True,
    default=1,
)
@option("-H", "--host", help="Server under this host", default="127.0.0.1", show_default=True)
@option(
    "-F",
    "--fd",
    "--file-descriptor",
    help="Bind to a socket from this file descriptor.",
    type=int,
    default=None,
    show_default=True,
)
@option("-U", "--uds", "--unix-domain-socket", help="Bind to a UNIX domain socket.", default=None, show_default=True)
@option("-d", "--debug", help="Run app in debug mode", is_flag=True)
@option("-P", "--pdb", "--use-pdb", help="Drop into PDB on an exception", is_flag=True)
def run_command(
    reload: bool,
    port: int,
    wc: int,
    host: str,
    fd: int | None,
    uds: str | None,
    debug: bool,
    reload_dir: tuple[str, ...],
    pdb: bool,
    ctx: Context,
) -> None:
    """Run a Litestar app.

    The app can be either passed as a module path in the form of <module name>.<submodule>:<app instance or factory>,
    set as an environment variable LITESTAR_APP with the same format or automatically discovered from one of these
    canonical paths: app.py, asgi.py, application.py or app/__init__.py. When auto-discovering application factories,
    functions with the name ``create_app`` are considered, or functions that are annotated as returning a ``Litestar``
    instance.
    """

    if debug:
        os.environ["LITESTAR_DEBUG"] = "1"

    if pdb:
        os.environ["LITESTAR_PDB"] = "1"

    if callable(ctx.obj):
        ctx.obj = ctx.obj()
    else:
        if debug:
            ctx.obj.app.debug = True
        if pdb:
            ctx.obj.app.pdb_on_exception = True

    env: LitestarEnv = ctx.obj
    app = env.app

    reload_dirs = env.reload_dirs or reload_dir

    host = env.host or host
    port = env.port if env.port is not None else port
    fd = env.fd if env.fd is not None else fd
    uds = env.uds or uds
    reload = env.reload or reload or bool(reload_dirs)
    workers = env.web_concurrency or wc

    console.rule("[yellow]Starting server process", align="left")

    show_app_info(app)

    if workers == 1 and not reload:
        uvicorn.run(
            app=env.app_path,
            host=host,
            port=port,
            fd=fd,
            uds=uds,
            factory=env.is_app_factory,
        )
    else:
        # invoke uvicorn in a subprocess to be able to use the --reload flag. see
        # https://github.com/litestar-org/litestar/issues/1191 and https://github.com/encode/uvicorn/issues/1045
        if sys.gettrace() is not None:
            console.print(
                "[yellow]Debugger detected. Breakpoints might not work correctly inside route handlers when running"
                " with the --reload or --workers options[/]"
            )

        process_args = {
            "reload": reload,
            "host": host,
            "port": port,
            "workers": workers,
            "factory": env.is_app_factory,
        }
        if fd is not None:
            process_args["fd"] = fd
        if uds is not None:
            process_args["uds"] = uds
        if reload_dirs:
            process_args["reload-dir"] = reload_dirs

        subprocess.run(
            [sys.executable, "-m", "uvicorn", env.app_path, *_convert_uvicorn_args(process_args)],  # noqa: S603
            check=True,
        )


@command(name="routes")
def routes_command(app: Litestar) -> None:  # pragma: no cover
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
            route_type = "WS" if isinstance(route, WebSocketRoute) else "ASGI"
            branch = tree.add(f"[green]{route.path}[/green] ({route_type})")
            branch.add(f"[blue]{route.route_handler.name or route.route_handler.handler_name}[/blue]")

    console.print(tree)
