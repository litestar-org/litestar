# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import codecs
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from multipart import (  # type: ignore[import-untyped]
    MultipartSegment,
    ParserError,
    ParserLimitReached,
    PushMultipartParser,
)

from litestar.datastructures.upload_file import UploadFile
from litestar.exceptions import ClientException
from litestar.exceptions.http_exceptions import RequestEntityTooLarge

__all__ = ("parse_content_header", "parse_multipart_form")


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from litestar.types import TypeDecodersSequence

_token = r"([\w!#$%&'*+\-.^_`|~]+)"  # noqa: S105
_quoted = r'"([^"]*)"'
_param = re.compile(rf";\s*{_token}=(?:{_token}|{_quoted})", re.ASCII)
_firefox_quote_escape = re.compile(r'\\"(?!; |\s*$)')
_allowed_charsets = frozenset({"utf-8", "ascii", "iso8859-1"})


def parse_content_header(value: str) -> tuple[str, dict[str, str]]:
    """Parse content-type and content-disposition header values.

    Args:
        value: A header string value to parse.

    Returns:
        A tuple containing the normalized header string and a dictionary of parameters.
    """
    value = _firefox_quote_escape.sub("%22", value)
    pos = value.find(";")
    if pos == -1:
        options: dict[str, str] = {}
    else:
        options = {
            m.group(1).lower(): m.group(2) or m.group(3).replace("%22", '"') for m in _param.finditer(value[pos:])
        }
        value = value[:pos]
    return value.strip().lower(), options


def _decode(data: bytearray, charset: str) -> str:
    try:
        codec = codecs.lookup(charset).name
        if codec not in _allowed_charsets:
            raise LookupError(codec)
        return data.decode(codec)
    except (LookupError, ValueError) as exc:
        raise ParserError(f"Invalid charset {charset!r}") from exc


async def _close_upload_files(fields: dict[str, list[Any]]) -> None:
    for values in fields.values():
        for value in values:
            if isinstance(value, UploadFile):
                await value.close()


async def parse_multipart_form(  # noqa: C901
    stream: AsyncGenerator[bytes, None],
    boundary: bytes,
    multipart_form_part_limit: int = 1000,
    type_decoders: TypeDecodersSequence | None = None,
) -> dict[str, Any]:
    """Parse multipart form data.

    Args:
        stream: Body of the request.
        boundary: Boundary of the multipart message.
        multipart_form_part_limit: Limit of the number of parts allowed.
        type_decoders: A sequence of type decoders to use.

    Returns:
        A dictionary of parsed results.
    """

    fields: defaultdict[str, list[Any]] = defaultdict(list)

    chunk = await anext(stream, b"")
    if not chunk:
        return fields

    data: UploadFile | bytearray = bytearray()

    try:
        with PushMultipartParser(boundary, max_segment_count=multipart_form_part_limit) as parser:
            segment: MultipartSegment | None = None
            while not parser.closed:
                for form_part in parser.parse(chunk):
                    if isinstance(form_part, MultipartSegment):
                        segment = form_part
                        if segment.filename:
                            data = UploadFile(
                                content_type=segment.content_type or "text/plain",
                                filename=segment.filename,
                                headers=dict(segment.headerlist),
                            )
                    elif form_part:
                        if isinstance(data, UploadFile):
                            await data.write(form_part)
                        else:
                            data.extend(form_part)
                    else:
                        # end of part
                        if segment is None:
                            # we have reached the end of a segment before we have
                            # received a complete header segment
                            raise ClientException("Unexpected eof in multipart/form-data")

                        if isinstance(data, UploadFile):
                            await data.seek(0)
                            fields[segment.name].append(data)
                        else:
                            # Always decode as string, even for empty data
                            fields[segment.name].append(
                                data.decode() if segment.charset is None else _decode(data, segment.charset)
                            )

                        # reset for next part
                        data = bytearray()
                        segment = None

                chunk = await anext(stream, b"")

    except (ParserError, UnicodeDecodeError) as exc:
        # if an exception is raised, make sure that all 'UploadFile's are closed
        if isinstance(data, UploadFile):
            await data.close()
        await _close_upload_files(fields)

        raise ClientException("Invalid multipart/form-data") from exc
    except ParserLimitReached:
        if isinstance(data, UploadFile):
            await data.close()
        await _close_upload_files(fields)

        raise RequestEntityTooLarge from None

    return {k: v if len(v) > 1 else v[0] for k, v in fields.items()}
