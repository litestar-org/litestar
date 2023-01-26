import asyncio
import inspect
import subprocess

from click import Choice, command, option
from rich.tree import Tree

from starlite import HTTPRoute, Starlite, WebSocketRoute
from starlite.cli.utils import StarliteCLIException, StarliteEnv, console, show_app_info
from starlite.enums import ServerEnum
from starlite.utils.helpers import unwrap_partial


@command(name="info")
def info_command(app: Starlite) -> None:
    """Show information about the detected Starlite app."""

    show_app_info(app)


@command(name="run")
@option("-r", "--reload", help="Reload server on changes", default=False, is_flag=True)
@option("-p", "--port", help="Serve under this port", type=int, default=8000, show_default=True)
@option("--host", help="Server under this host", default="127.0.0.1", show_default=True)
@option("--debug", help="Run app in debug mode", is_flag=True)
@option(
    "--server",
    help="Server to run the app with",
    type=Choice([server.value for _, server in ServerEnum.__members__.items()]),
    default=ServerEnum.UVICORN.value,
    show_default=True,
)
def run_command(
    reload: bool,
    port: int,
    host: str,
    debug: bool,
    server: ServerEnum,
    env: StarliteEnv,
    app: Starlite,
) -> None:
    """Run a Starlite app.

    The app can be either passed as a module path in the form of <module name>.<submodule>:<app instance or factory>,
    set as an environment variable STARLITE_APP with the same format or automatically discovered from one of these
    canonical paths: app.py, asgi.py, application.py or app/__init__.py. When autodiscovering application factories,
    functions with the name ``create_app`` are considered, or functions that are annotated as returning a ``Starlite``
    instance.
    """

    if debug or env.debug:
        app.debug = True

    show_app_info(app)

    console.rule("[yellow]Starting server process", align="left")
    if server == ServerEnum.UVICORN.value:
        try:
            import uvicorn

            uvicorn.run(
                env.app_path,
                reload=env.reload or reload,
                host=env.host or host,
                port=env.port or port,
                factory=env.is_app_factory,
            )
        except ImportError:
            raise StarliteCLIException("Uvicorn needs to be installed to run an app")  # pylint: disable=W0707

    elif server == ServerEnum.HYPERCORN.value:
        try:
            import hypercorn  # pyright: ignore[reportMissingImports]
            from hypercorn.asyncio import serve  # pyright: ignore[reportMissingImports]

            config = hypercorn.Config()
            config.bind = [f"{env.host or host}:{env.port or port}"]
            config.use_reloader = env.reload or reload
            asyncio.run(serve(env.app_path, config))
        except ImportError:
            raise StarliteCLIException(  # pylint: disable=W0707
                "--server option is set to hypercorn, so Hypercorn needs to be installed to run the app"
            )

    elif server == ServerEnum.DAPHNE.value:
        try:
            import daphne  # noqa: F401 # pyright: ignore
        except ImportError:
            raise StarliteCLIException(  # pylint: disable=W0707
                "--server option is set to daphne, so Daphne needs to be installed to run the app"
            )
        subprocess.run(["daphne", env.app_path, "-b", str(env.host or host), "-p", str(env.port or port)], check=True)


@command(name="routes")
def routes_command(app: Starlite) -> None:  # pragma: no cover
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
