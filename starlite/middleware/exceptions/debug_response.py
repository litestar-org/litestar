import inspect
from html import escape
from pathlib import Path
from traceback import format_exception
from typing import TYPE_CHECKING, List

from starlite.enums import MediaType
from starlite.response import Response
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from starlite.connection import Request

tpl_dir = Path(__file__).parent / "templates"


def get_symbol_name(frame: inspect.FrameInfo) -> str:
    """Return full name of the function that is being executed by the given
    frame."""
    classname = ""
    locals_dict = frame.frame.f_locals
    # probably we are inside of an instance method
    # this piece assumes that the code uses standard names "self" and "cls"
    # in instance and class methods
    if locals_dict.get("self"):
        classname = f"{type(locals_dict['self']).__name__}."
    # inside a class method?
    elif locals_dict.get("cls"):
        classname = f"{locals_dict['cls'].__name__}."

    return f"{classname}{frame.function}"


def create_line_html(
    line: str,
    line_no: int,
    frame_index: int,
    idx: int,
) -> str:
    """Return html representation of a line including real line number in the
    source code."""
    template = '<tr class="{line_class}"><td class="line_no">{line_no}</td><td class="code_line">{line}</td></tr>'
    data = {
        "line_no": line_no - frame_index + idx,
        "line": escape(line).replace(" ", "&nbsp"),
        "line_class": "current_line" if idx == frame_index else "",
    }
    return template.format(**data)


def create_frame_html(frame: inspect.FrameInfo, collapsed: bool) -> str:
    """Return html representation of the given frame object including filename
    containing source code and name of the function being executed."""
    frame_tpl = (tpl_dir / "frame.html").read_text()

    code_lines: List[str] = []
    for idx, line in enumerate(frame.code_context or []):
        code_lines.append(create_line_html(line, frame.lineno, frame.index or 0, idx))

    data = {
        "file": escape(frame.filename),
        "line": frame.lineno,
        "symbol_name": escape(get_symbol_name(frame)),
        "code": "".join(code_lines),
        "frame_class": "collapsed" if collapsed else "",
    }
    return frame_tpl.format(**data)


def create_exception_html(exc: BaseException, frame_limit: int) -> str:
    """Return html representation of exception frames."""
    frames = inspect.getinnerframes(exc.__traceback__, frame_limit) if exc.__traceback__ else []
    result = []
    for idx, frame in enumerate(reversed(frames)):
        result.append(create_frame_html(frame=frame, collapsed=(idx > 0)))

    return "".join(result)


def create_html_response_contet(exc: Exception, request: "Request", frame_limit: int = 15) -> str:
    """Return exception traceback in HTML."""
    exception_data: List[str] = [create_exception_html(exc, frame_limit)]
    cause = exc.__cause__
    while cause:
        cause_data = create_exception_html(cause, frame_limit)
        cause_header = '<h4 class="cause-header">The above exception was caused by</h4>'
        cause_error_description = f"<h3><span>{cause}</span></h3>"
        cause_error = f"<h4><span>{escape(cause.__class__.__name__)}</span></h4>"
        exception_data.append(
            f'<div class="cause-wrapper">{cause_header}{cause_error}{cause_error_description}{cause_data}</div>'
        )
        cause = cause.__cause__

    scripts = (tpl_dir / "scripts.js").read_text()
    styles = (tpl_dir / "styles.css").read_text()
    body_tpl = (tpl_dir / "body.html").read_text()
    return body_tpl.format(
        scripts=scripts,
        styles=styles,
        error=f"<span>{escape(exc.__class__.__name__)}</span> on {request.method} {request.url.path}",
        error_description=f"{exc}",
        exception_data="".join(exception_data),
    )


def create_plain_text_response_contet(exc: Exception) -> str:
    """Return exception traceback in plain text."""
    return "".join(format_exception(type(exc), value=exc, tb=exc.__traceback__))


def create_debug_response(request: "Request", exc: Exception) -> Response:
    """Create debug response either in plain text or html depending on client
    capabilities."""
    if "text/html" in request.headers.get("accept", ""):
        content = create_html_response_contet(exc=exc, request=request)
        media_type = MediaType.HTML
    else:
        content = create_plain_text_response_contet(exc)
        media_type = MediaType.TEXT

    return Response(content=content, media_type=media_type, status_code=HTTP_500_INTERNAL_SERVER_ERROR)
