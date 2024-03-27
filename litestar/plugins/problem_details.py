from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar

from litestar.connection.request import Request
from litestar.exceptions.http_exceptions import HTTPException
from litestar.plugins.base import InitPluginProtocol
from litestar.response.base import Response
from litestar.serialization.msgspec_hooks import encode_json
from litestar.types.callable_types import ExceptionHandler, ExceptionT

if TYPE_CHECKING:
    from litestar.config.app import AppConfig

ProblemDetailsExceptionT = TypeVar("ProblemDetailsExceptionT", bound="ProblemDetailsException")
ProblemDetailsExceptionHandlerType = Callable[[Request, ProblemDetailsExceptionT], Response]
ExceptionToProblemDetailMapType = Mapping[type[ExceptionT], Callable[[ExceptionT], ProblemDetailsExceptionT]]


def _problem_details_exception_handler(request: Request, exc: ProblemDetailsException) -> Response:
    return exc.to_response(request)


def _create_exception_handler(
    exc_to_problem_details_exc_fn: Callable[[ExceptionT], ProblemDetailsException], exc_type: type[ExceptionT]
) -> ExceptionHandler:
    def _exception_handler(req: Request, exc: exc_type) -> Response:
        problem_details_exc = exc_to_problem_details_exc_fn(exc)

        return problem_details_exc.to_response(req)

    return _exception_handler


class ProblemDetailsException(HTTPException):
    _PROBLEM_DETAIL_HEADER = "application/problem+json"

    def __init__(
        self,
        type_: str = "about:blank",
        status_code: int | None = None,
        title: str | None = None,
        instance: str | None = None,
        detail: str | dict[str, Any] | list[Any] | None = None,
        extra: dict[str, Any] | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        self.type_ = type_
        self.status_code = status_code or self.status_code
        self.title = title
        self.instance = instance
        self.detail = detail  # type: ignore
        self.extra = extra
        self.headers = headers

    def to_response(self, request: Request) -> Response:
        problem_details = {"type": self.type_, "status": self.status_code}
        if self.title is not None:
            problem_details["title"] = self.title
        if self.instance is not None:
            problem_details["instance"] = self.instance
        if self.detail is not None:
            problem_details["detail"] = self.detail
        if self.extra is not None:
            problem_details.update(self.extra)

        content = encode_json(problem_details, request.route_handler.default_serializer)
        headers = self.headers or {}
        headers["content-type"] = self._PROBLEM_DETAIL_HEADER

        return Response(content, headers=headers)

    @classmethod
    def from_http_exception(cls, exc: HTTPException) -> ProblemDetailsException:
        return ProblemDetailsException(status_code=exc.status_code)


@dataclass
class ProblemDetailsConfig:
    exception_handler: ProblemDetailsExceptionHandlerType = _problem_details_exception_handler
    """The exception handler used for ``ProblemdetailsException.``"""

    enable_for_all_http_exceptions: bool = False
    """Flag indicating whether to convert all exceptions into ``ProblemDetailsException.``"""

    exception_to_problem_detail_map: ExceptionToProblemDetailMapType | None = None
    """A mapping to convert exceptions into ``ProblemDetailsException.``

    All exceptions provided in this will get a custom exception handler where these exceptions
    are converted into ``ProblemDetailException`` before handling them.
    """


class ProblemDetailsPlugin(InitPluginProtocol):
    def __init__(self, config: ProblemDetailsConfig | None = None):
        self.config = config or ProblemDetailsConfig()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.exception_handlers[ProblemDetailsException] = self.config.exception_handler

        if self.config.enable_for_all_http_exceptions:
            app_config.exception_handlers[HTTPException] = _create_exception_handler(
                ProblemDetailsException.from_http_exception, HTTPException
            )

        if conversion_map := self.config.exception_to_problem_detail_map:
            for exc_type, conversion_fn in conversion_map.items():
                app_config.exception_handlers[exc_type] = _create_exception_handler(conversion_fn, exc_type)

        return app_config
