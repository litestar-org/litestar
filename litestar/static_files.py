from __future__ import annotations

import functools
import os
from os.path import commonpath
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Any, Literal, cast

from litestar.exceptions import ImproperlyConfiguredException, NotFoundException
from litestar.file_system import (
    AnyFileSystem,
    BaseFileSystem,
    FileInfo,
    FileSystemRegistry,
    LinkableFileSystem,
    maybe_wrap_fsspec_file_system,
)
from litestar.handlers import get, head
from litestar.response.file import ASGIFileResponse
from litestar.router import Router
from litestar.status_codes import HTTP_404_NOT_FOUND
from litestar.types import Empty
from litestar.utils import normalize_path

__all__ = ("create_static_files_router",)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from litestar import Request
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
    directories: Sequence[PathType],
    file_system: AnyFileSystem | str | None = None,
    send_as_attachment: bool = False,
    html_mode: bool = False,
    name: str = "static",
    after_request: AfterRequestHookHandler | None = None,
    after_response: AfterResponseHookHandler | None = None,
    before_request: BeforeRequestHookHandler | None = None,
    cache_control: CacheControlHeader | None = None,
    exception_handlers: ExceptionHandlersMap | None = None,
    guards: Sequence[Guard] | None = None,
    include_in_schema: bool | EmptyType = Empty,
    middleware: Sequence[Middleware] | None = None,
    opt: Mapping[str, Any] | None = None,
    security: Sequence[SecurityRequirement] | None = None,
    tags: Sequence[str] | None = None,
    router_class: type[Router] = Router,
    allow_symlinks_outside_directory: bool | None = None,
) -> Router:
    """Create a router with handlers to serve static files.

    Args:
        path: Path to serve static files under
        directories: Directories to serve static files from
        file_system: The file system to load the file from. Instances of
            :class:`~litestar.file_system.BaseFileSystem`, :class:`fsspec.spec.AbstractFileSystem`,
            :class:`fsspec.asyn.AsyncFileSystem` will be used directly. If passed string, use it to look up the
            corresponding file system from the :class:`~litestar.file_system.FileSystemRegistry`. If not given, the
            file will be loaded from :attr:`~litestar.file_system.FileSystemRegistry.default`
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
        allow_symlinks_outside_directory: Allow serving files that link a path inside a
            base directory (as specified in 'directories') to a path outside it. This
            should be handled with caution, as it allows potentially unintended access
            to files outside the defined 'directories' via symlink chains. For
            'file_system's that do not support symlinking (i.e. do not inherit from
            'LinkableFileSystem'), raise a :exc:`TypeError` when given a value other
            than ``None``. For file systems that support symlinks, default to ``False``
    """

    if file_system is not None:
        file_system = maybe_wrap_fsspec_file_system(file_system)
        _validate_allow_symlinks_outside_directory(file_system, allow_symlinks_outside_directory)

    resolved_directories = tuple(os.path.normpath(Path(p).absolute()) for p in directories)

    _validate_config(path=path, directories=resolved_directories)
    path = normalize_path(path)

    headers = None
    if cache_control:
        headers = {cache_control.HEADER_NAME: cache_control.to_header()}

    @get("{file_path:path}", name=name)
    async def get_handler(file_path: PurePath, request: Request) -> ASGIFileResponse:
        return await _handler(
            path=file_path.as_posix(),
            is_head_response=False,
            directories=resolved_directories,
            fs=file_system,
            is_html_mode=html_mode,
            send_as_attachment=send_as_attachment,
            headers=headers,
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
            request=request,
        )

    @head("/{file_path:path}", name=f"{name}/head")
    async def head_handler(file_path: PurePath, request: Request) -> ASGIFileResponse:
        return await _handler(
            path=file_path.as_posix(),
            is_head_response=True,
            directories=resolved_directories,
            fs=file_system,
            is_html_mode=html_mode,
            send_as_attachment=send_as_attachment,
            headers=headers,
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
            request=request,
        )

    handlers = [get_handler, head_handler]

    if html_mode:

        @get("/", name=f"{name}/index")
        async def index_handler(request: Request) -> ASGIFileResponse:
            return await _handler(
                path="/",
                is_head_response=False,
                directories=resolved_directories,
                fs=file_system,
                is_html_mode=True,
                send_as_attachment=send_as_attachment,
                headers=headers,
                allow_symlinks_outside_directory=allow_symlinks_outside_directory,
                request=request,
            )

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


async def _handler(
    *,
    path: str,
    is_head_response: bool,
    directories: tuple[str, ...],
    send_as_attachment: bool,
    fs: BaseFileSystem | str | None,
    is_html_mode: bool,
    headers: dict[str, str] | None,
    allow_symlinks_outside_directory: bool | None,
    request: Request,
) -> ASGIFileResponse:
    split_path = path.split("/")
    filename = split_path[-1]
    joined_path = Path(*split_path)

    fs = _get_file_system(fs, request)

    resolved_path, fs_info = await _get_fs_info(
        directories=directories,
        file_path=joined_path,
        fs=fs,
        allow_symlinks_outside_directory=allow_symlinks_outside_directory,
    )
    content_disposition_type: Literal["inline", "attachment"] = "attachment" if send_as_attachment else "inline"

    if is_html_mode and fs_info and fs_info["type"] == "directory":
        filename = "index.html"
        resolved_path, fs_info = await _get_fs_info(
            directories=directories,
            file_path=Path(resolved_path or joined_path) / filename,
            fs=fs,
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
        )

    if fs_info and fs_info["type"] == "file":
        return ASGIFileResponse(
            file_path=resolved_path or joined_path,
            file_info=fs_info,
            file_system=fs,
            filename=filename,
            content_disposition_type=content_disposition_type,
            is_head_response=is_head_response,
            headers=headers,
        )

    if is_html_mode:
        # for some reason coverage doesn't catch these two lines
        filename = "404.html"  # pragma: no cover
        resolved_path, fs_info = await _get_fs_info(  # pragma: no cover
            directories=directories,
            file_path=filename,
            fs=fs,
            allow_symlinks_outside_directory=allow_symlinks_outside_directory,
        )

        if fs_info and fs_info["type"] == "file":
            return ASGIFileResponse(
                file_path=resolved_path or joined_path,
                file_info=fs_info,
                file_system=fs,
                filename=filename,
                status_code=HTTP_404_NOT_FOUND,
                content_disposition_type=content_disposition_type,
                is_head_response=is_head_response,
                headers=headers,
            )

    raise NotFoundException(
        f"no file or directory match the path {resolved_path or joined_path} was found"
    )  # pragma: no cover


@functools.cache
def _validate_allow_symlinks_outside_directory(
    fs: BaseFileSystem,
    allow_symlinks_outside_directory: bool | None,
) -> bool:
    is_linkable_fs = isinstance(fs, LinkableFileSystem)
    if is_linkable_fs:
        if allow_symlinks_outside_directory is None:
            return False
        return allow_symlinks_outside_directory

    # not a linkable fs, so 'allow' following symlinks blindly, i.e. do not attempt to
    # resolve symlinks
    if allow_symlinks_outside_directory is None:
        return True

    raise TypeError(
        "'allow_symlinks_outside_directory' not supported for file system "
        f"{type(fs)!r}. This option can only be used with a file system that supports "
        "symlinks. For a file system to support symlinks, it must implement '"
        "LinkableFileSystem'"
    )


async def _get_fs_info(
    directories: Sequence[PathType],
    file_path: PathType,
    fs: BaseFileSystem | LinkableFileSystem,
    allow_symlinks_outside_directory: bool | None,
) -> tuple[Path, FileInfo] | tuple[None, None]:
    """Return the resolved path and a :class:`stat_result <os.stat_result>`"""
    allow_symlinks_outside_directory = _validate_allow_symlinks_outside_directory(fs, allow_symlinks_outside_directory)

    for directory in directories:
        try:
            joined_path = Path(directory, file_path)
            file_info = await fs.info(joined_path)
            if allow_symlinks_outside_directory:
                # we want to read 'through' a symlink, so just get the normpath.
                # this flag may also be set if the file system has no notion of symlinks
                normalized_file_path = os.path.normpath(joined_path)
            else:
                # we do not want to read 'through' a symlink, so ask the fs to resolve
                # potential symlinks and return the real path to the file.
                # this means that if our path is '/path/to/file' and a symlink pointing
                # to '/some/other/location', the latter part will be used to check if
                # we are allowed to serve this file.
                # in this example, if the configured base directory is '/path/to', we
                # would not serve the file located at '/path/to/file', since it links to
                # '/some/other/location', which is *not* a subpath of '/path/to'
                normalized_file_path = await cast("LinkableFileSystem", fs).resolve_symlinks(joined_path)

            directory_path = str(directory)
            if (
                file_info
                and commonpath([directory_path, file_info["name"], joined_path]) == directory_path
                and os.path.commonpath([directory, normalized_file_path]) == directory_path
            ):
                return joined_path, file_info
        except FileNotFoundError:
            continue
    return None, None


def _validate_config(path: str, directories: tuple[PathType, ...]) -> None:
    if not path:
        raise ImproperlyConfiguredException("path must be a non-zero length string")

    if not directories or not any(bool(d) for d in directories):
        raise ImproperlyConfiguredException("directories must include at least one path")

    if "{" in path:
        raise ImproperlyConfiguredException("path parameters are not supported for static files")


def _get_file_system(fs: BaseFileSystem | str | None, request: Request) -> BaseFileSystem:
    if isinstance(fs, BaseFileSystem):
        return fs

    registry = request.app.plugins.get(FileSystemRegistry)

    if isinstance(fs, str):
        return registry[fs]

    return registry.default
