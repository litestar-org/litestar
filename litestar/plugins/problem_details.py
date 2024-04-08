from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar

from litestar.connection.request import Request
from litestar.exceptions.http_exceptions import HTTPException
from litestar.plugins.base import InitPluginProtocol
from litestar.response.base import Response
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


def _http_exception_to_problem_detail_exception(exc: HTTPException) -> ProblemDetailsException:
    return ProblemDetailsException(status_code=exc.status_code, detail=exc.detail, extra=exc.extra, headers=exc.headers)


class ProblemDetailsException(HTTPException):
    """A problem details exception as per RFC 9457."""

    _PROBLEM_DETAILS_MEDIA_TYPE = "application/problem+json"

    def __init__(
        self,
        *args: Any,
        detail: str = "",
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | list[Any] | None = None,
        type_: str = "about:blank",
        title: str | None = None,
        instance: str | None = None,
    ) -> None:
        """Initialize ``ProblemDetailsException``.

        Args:
            *args: if ``detail`` kwarg not provided, first arg should be error detail.
            detail: Exception details or message. Will default to args[0] if not provided.
            status_code: Exception HTTP status code.
            headers: Headers to set on the response.
            extra: An extra mapping to attach to the exception.
            type_: The type field in the problem details.
            title: The title field in the problem details.
            instance: The instance field in the problem details.
        """

        super().__init__(*args, detail=detail, status_code=status_code, headers=headers, extra=extra)

        self.type_ = type_
        self.title = title
        self.instance = instance

    def to_response(self, request: Request) -> Response:
        """Convert the problem details exception into a ``Response.``"""

        problem_details = {"type": self.type_, "status": self.status_code}
        for attr in ("title", "instance", "detail", "extra"):
            if (value := getattr(self, attr, None)) is not None:
                problem_details[attr] = value

        return Response(
            problem_details,
            headers=self.headers,
            media_type=self._PROBLEM_DETAILS_MEDIA_TYPE,
            status_code=self.status_code,
        )


@dataclass
class ProblemDetailsConfig:
    """The configuration object for ``ProblemDetailsPlugin.``"""

    exception_handler: ProblemDetailsExceptionHandlerType = _problem_details_exception_handler
    """The exception handler used for ``ProblemdetailsException.``"""

    enable_for_all_http_exceptions: bool = False
    """Flag indicating whether to convert all exceptions into ``ProblemDetailsException.``"""

    exception_to_problem_detail_map: ExceptionToProblemDetailMapType = field(default_factory=dict)
    """A mapping to convert exceptions into ``ProblemDetailsException.``

    All exceptions provided in this will get a custom exception handler where these exceptions
    are converted into ``ProblemDetailException`` before handling them.
    """


class ProblemDetailsPlugin(InitPluginProtocol):
    """A plugin to convert exceptions into problem details as per RFC 9457."""

    def __init__(self, config: ProblemDetailsConfig | None = None):
        self.config = config or ProblemDetailsConfig()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.exception_handlers[ProblemDetailsException] = self.config.exception_handler

        if self.config.enable_for_all_http_exceptions:
            app_config.exception_handlers[HTTPException] = _create_exception_handler(
                _http_exception_to_problem_detail_exception, HTTPException
            )

        for exc_type, conversion_fn in self.config.exception_to_problem_detail_map.items():
            app_config.exception_handlers[exc_type] = _create_exception_handler(conversion_fn, exc_type)

        return app_config
