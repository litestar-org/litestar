from __future__ import annotations

from click import Context, group, option, pass_context

from ._utils import LitestarEnv, LitestarExtensionGroup
from .commands import core, schema, sessions

__all__ = ("litestar_group",)


@group(cls=LitestarExtensionGroup)
@option("--app", "app_path", help="Module path to a Litestar application")
@pass_context
def litestar_group(ctx: Context, app_path: str | None) -> None:
    """Litestar CLI."""

    ctx.obj = lambda: LitestarEnv.from_env(app_path)


# add sub commands here

litestar_group.add_command(core.info_command)
litestar_group.add_command(core.run_command)
litestar_group.add_command(core.routes_command)
litestar_group.add_command(core.version_command)
litestar_group.add_command(sessions.sessions_group)
litestar_group.add_command(schema.schema_group)
