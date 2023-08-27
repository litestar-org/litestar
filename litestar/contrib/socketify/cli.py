from __future__ import annotations

import multiprocessing
import os

import click
from click import Context, command, option

from litestar.cli._utils import LitestarEnv, console, show_app_info


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
    from socketify import ASGI

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

    console.rule("[yellow]Starting [blue]socketify[/] server process[/]", align="left")

    show_app_info(app)
    ASGI(app=app, lifespan=False).listen(port).run(workers=workers)
