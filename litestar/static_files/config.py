from __future__ import annotations

from pathlib import PurePath  # noqa: TCH003
from typing import TYPE_CHECKING, Any, Sequence

from litestar.exceptions import ImproperlyConfiguredException
from litestar.file_system import BaseLocalFileSystem
from litestar.handlers import get, head
from litestar.response.file import ASGIFileResponse  # noqa: TCH001
from litestar.router import Router
from litestar.static_files.base import StaticFiles
from litestar.types import Empty
from litestar.utils import normalize_path

__all__ = ("create_static_files_router",)

if TYPE_CHECKING:
    from litestar.datastructures import CacheControlHeader
    from litestar.openapi.spec import SecurityRequirement
    from litestar.types import (
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        BeforeRequestHookHandler,
        EmptyType,
        ExceptionHandlersMap,
        Guard,
        Middleware,
        PathType,
    )


def create_static_files_router(
    path: str,
    directories: list[PathType],
    file_system: Any = None,
    send_as_attachment: bool = False,
    html_mode: bool = False,
    name: str = "static",
    after_request: AfterRequestHookHandler | None = None,
    after_response: AfterResponseHookHandler | None = None,
    before_request: BeforeRequestHookHandler | None = None,
    cache_control: CacheControlHeader | None = None,
    exception_handlers: ExceptionHandlersMap | None = None,
    guards: list[Guard] | None = None,
    include_in_schema: bool | EmptyType = Empty,
    middleware: Sequence[Middleware] | None = None,
    opt: dict[str, Any] | None = None,
    security: Sequence[SecurityRequirement] | None = None,
    tags: Sequence[str] | None = None,
    router_class: type[Router] = Router,
    resolve_symlinks: bool = True,
) -> Router:
    """Create a router with handlers to serve static files.

    Args:
        path: Path to serve static files under
        directories: Directories to serve static files from
        file_system: A *file system* implementing
            :class:`~litestar.types.FileSystemProtocol`.
            `fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ can be passed
            here as well
        send_as_attachment: Whether to send the file as an attachment
        html_mode: When in HTML:
            - Serve an ``index.html`` file from ``/``
            - Serve ``404.html`` when a file could not be found
        name: Name to pass to the generated handlers
        after_request: ``after_request`` handlers passed to the router
        after_response: ``after_response`` handlers passed to the router
        before_request: ``before_request`` handlers passed to the router
        cache_control: ``cache_control`` passed to the router
        exception_handlers: Exception handlers passed to the router
        guards: Guards  passed to the router
        include_in_schema: Include the routes / router in the OpenAPI schema
        middleware: Middlewares passed to the router
        opt: Opts passed to the router
        security: Security options passed to the router
        tags: ``tags`` passed to the router
        router_class: The class used to construct a router from
        resolve_symlinks: Resolve symlinks of ``directories``
    """

    if file_system is None:
        file_system = BaseLocalFileSystem()

    _validate_config(path=path, directories=directories, file_system=file_system)
    path = normalize_path(path)

    headers = None
    if cache_control:
        headers = {cache_control.HEADER_NAME: cache_control.to_header()}

    static_files = StaticFiles(
        is_html_mode=html_mode,
        directories=directories,
        file_system=file_system,
        send_as_attachment=send_as_attachment,
        resolve_symlinks=resolve_symlinks,
        headers=headers,
    )

    @get("{file_path:path}", name=name)
    async def get_handler(file_path: PurePath) -> ASGIFileResponse:
        return await static_files.handle(path=file_path.as_posix(), is_head_response=False)

    @head("/{file_path:path}", name=f"{name}/head")
    async def head_handler(file_path: PurePath) -> ASGIFileResponse:
        return await static_files.handle(path=file_path.as_posix(), is_head_response=True)

    handlers = [get_handler, head_handler]

    if html_mode:

        @get("/", name=f"{name}/index")
        async def index_handler() -> ASGIFileResponse:
            return await static_files.handle(path="/", is_head_response=False)

        handlers.append(index_handler)

    return router_class(
        after_request=after_request,
        after_response=after_response,
        before_request=before_request,
        cache_control=cache_control,
        exception_handlers=exception_handlers,
        guards=guards,
        include_in_schema=include_in_schema,
        middleware=middleware,
        opt=opt,
        path=path,
        route_handlers=handlers,
        security=security,
        tags=tags,
    )


def _validate_config(path: str, directories: list[PathType], file_system: Any) -> None:
    if not path:
        raise ImproperlyConfiguredException("path must be a non-zero length string,")

    if not directories or not any(bool(d) for d in directories):
        raise ImproperlyConfiguredException("directories must include at least one path.")

    if "{" in path:
        raise ImproperlyConfiguredException("path parameters are not supported for static files")

    if not (callable(getattr(file_system, "info", None)) and callable(getattr(file_system, "open", None))):
        raise ImproperlyConfiguredException("file_system must adhere to the FileSystemProtocol type")
