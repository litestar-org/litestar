"""The contents of this file incorporate code adapted from https://github.com/pallets/werkzeug.

Copyright 2007 Pallets
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:
1.  Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
2.  Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
3.  Neither the name of the copyright holder nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote_to_bytes

from orjson import JSONDecodeError, loads

from starlite.datastructures import Headers, UploadFile


@dataclass
class FieldEvent:
    """Container for multipart field message."""

    __slots__ = (
        "name",
        "headers",
        "filename",
    )

    name: str
    headers: Dict[str, str]
    filename: Optional[str]


@dataclass
class DataEvent:
    """Container for multipart data message."""

    __slots__ = (
        "data",
        "more_data",
    )

    data: bytes
    more_data: bool


def get_buffer_last_newline(buffer: bytearray) -> int:
    """Return the position of the last new line break. Handles malformed new line formatting.

    Notes:
        - This function makes use of rindex specifically because -1 is also used. Hence, using find cannot work.
        - Multipart line breaks MUST be CRLF by RFC-7578, except that many implementations break this and either
            use CR or LF alone.

    Returns:
        Last new line index.
    """
    try:
        last_nl = buffer.rindex(b"\n")
    except ValueError:
        last_nl = len(buffer)
    try:
        last_cr = buffer.rindex(b"\r")
    except ValueError:
        last_cr = len(buffer)

    return min(last_nl, last_cr)


def parse_multipart_headers(data: bytes) -> Dict[str, str]:
    """Given a message byte string, parse the headers component of it and return a dictionary of normalized key/value
    pairs.

    Args:
        data: A byte string.

    Returns:
        A string / string dictionary of parsed values.
    """
    data = RFC2231_HEADER_CONTINUATION_RE.sub(b" ", data)

    return {
        k.strip().lower(): v.strip()
        for k, v in [line.decode().split(":", 1) for line in data.splitlines() if line.strip() != b""]
    }


def unquote_header_value(value: str, is_filename: bool = False) -> str:
    """Unquote a header value. This does not use the real unquoting but what browsers are actually using for quoting.

    Args:
        value: Value to unquoted.
        is_filename: Boolean flag dictating whether the value is a filename.

    Returns:
        The unquoted value.
    """
    if value and value[0] == value[-1] == '"':
        value = value[1:-1]
        if not is_filename or value[:2] != "\\\\":
            return value.replace("\\\\", "\\").replace('\\"', '"')
    return value


def parse_options_header(value: Optional[str]) -> Tuple[str, Dict[str, str]]:
    """Parse a 'Content-Type' or 'Content-Disposition' header, returning the header value and any options as a
    dictionary.

    Args:
        value: An optional header string.

    Returns:
        A tuple with the parsed value and a dictionary containing any options send in it.
    """
    if not value:
        return "", {}

    result: List[str] = []

    value = "," + value.replace("\n", ",")
    while value:
        match = OPTION_HEADER_START_MIME_RE.match(value)
        if not match:
            break

        result.append(match.group(1))  # mimetype

        options: Dict[str, str] = {}
        rest = match.group(2)
        encoding: Optional[str]
        continued_encoding: Optional[str] = None

        while rest:
            optmatch = OPTION_HEADER_PIECE_RE.match(rest)
            if not optmatch:
                break

            option, count, encoding, _, option_value = optmatch.groups()
            if count and encoding:
                continued_encoding = encoding
            elif count:
                encoding = continued_encoding
            else:
                continued_encoding = None

            option = unquote_header_value(option).lower()

            if option_value is not None:
                option_value = unquote_header_value(option_value, option == "filename")

                if encoding is not None:
                    option_value = unquote_to_bytes(option_value).decode(encoding)

            if not count:
                options[option] = option_value or ""
            elif option_value is not None:
                options[option] = options.get(option, "") + option_value

            rest = rest[optmatch.end() :]
        return result[0], options

    return result[0] if result else "", {}


LINE_BREAK = b"(?:\r\n|\n|\r)"
BLANK_LINE_RE = re.compile(b"(?:\r\n\r\n|\r\r|\n\n)", re.MULTILINE)
LINE_BREAK_RE = re.compile(LINE_BREAK, re.MULTILINE)
RFC2231_HEADER_CONTINUATION_RE = re.compile(b"%s[ \t]" % LINE_BREAK, re.MULTILINE)
SEARCH_BUFFER_LENGTH = 8
OPTION_HEADER_START_MIME_RE = re.compile(r",\s*([^;,\s]+)([;,]\s*.+)?")
OPTION_HEADER_PIECE_RE = re.compile(
    r"""
    ;\s*,?\s*  # newlines were replaced with commas
    (?P<key>
        "[^"\\]*(?:\\.[^"\\]*)*"  # quoted string
    |
        [^\s;,=*]+  # token
    )
    (?:\*(?P<count>\d+))?  # *1, optional continuation index
    \s*
    (?:  # optionally followed by =value
        (?:  # equals sign, possibly with encoding
            \*\s*=\s*  # * indicates extended notation
            (?:  # optional encoding
                (?P<encoding>[^\s]+?)
                '(?P<language>[^\s]*?)'
            )?
        |
            =\s*  # basic notation
        )
        (?P<value>
            "[^"\\]*(?:\\.[^"\\]*)*"  # quoted string
        |
            [^;,]+  # token
        )?
    )?
    \s*
    """,
    flags=re.VERBOSE,
)


class ProcessingStage(Enum):
    """The stages in which the multipart parser state machine can be in."""

    PREAMBLE = 1
    PART = 2
    DATA = 3
    EPILOGUE = 4
    COMPLETE = 5


def load_field_data(current_field_data: bytes) -> Any:
    """Load the given field data - try as JSON, if failing decode into string.

    Args:
        current_field_data: A byte string to load.

    Returns:
        An arbitrary value.
    """
    try:
        return loads(current_field_data)
    except JSONDecodeError:
        try:
            return current_field_data.decode()
        except UnicodeDecodeError:
            return current_field_data.decode("latin-1")


class MultipartParser:
    """Parser for multi-part form data.

    This class is a stateful decoder of a data stream.
    """

    __slots__ = (
        "boundary_re",
        "buffer",
        "headers",
        "message_boundary",
        "preamble_re",
        "processing_stage",
        "search_position",
        "stream",
    )

    def __init__(
        self,
        message_boundary: str,
        stream: AsyncGenerator[bytes, None],
    ) -> None:
        """Parse for multipart messages.

        Args:
            message_boundary: The message message_boundary as specified by [RFC7578][https://www.rfc-editor.org/rfc/rfc7578]
            headers: A mapping of headers.
            stream: An async generator yielding a stream.
        """
        self.buffer = bytearray()
        self.message_boundary = message_boundary.encode("latin-1")
        self.processing_stage = ProcessingStage.PREAMBLE
        self.search_position = 0
        self.stream = stream

        # The preamble must end with a message_boundary where the message_boundary is prefixed by a line break, RFC2046.
        self.preamble_re = re.compile(
            rb"%s?--%s(--[^\S\n\r]*%s?|[^\S\n\r]*%s)"
            % (LINE_BREAK, re.escape(self.message_boundary), LINE_BREAK, LINE_BREAK),
            re.MULTILINE,
        )
        # A message_boundary must include a line break prefix and suffix, and may include trailing whitespace.
        self.boundary_re = re.compile(
            rb"%s--%s(--[^\S\n\r]*%s?|[^\S\n\r]*%s)"
            % (LINE_BREAK, re.escape(self.message_boundary), LINE_BREAK, LINE_BREAK),
            re.MULTILINE,
        )

    async def parse(self) -> List[Tuple[str, Union[str, UploadFile]]]:
        """Parse the data stream into a tuple of key value pairs.

        Returns:
            A tuple of parsed key value pairs.
        """
        async for chunk in self.stream:
            self.buffer.extend(chunk)

        output: List[Tuple[str, Union[str, UploadFile]]] = []
        field_event: Optional[FieldEvent] = None
        current_field_data = bytearray()

        while self.processing_stage != ProcessingStage.COMPLETE:
            if field_event and (event := self._process_data()):
                file_data: Optional[UploadFile] = None
                if field_event.filename:
                    file_data = UploadFile(
                        filename=field_event.filename,
                        headers=field_event.headers,
                        content_type=field_event.headers.get("content-type", ""),
                    )
                    await file_data.write(event.data)
                else:
                    current_field_data.extend(event.data)

                if event.more_data:
                    continue

                if file_data:
                    await file_data.seek(0)
                    output.append((field_event.name, file_data))
                else:
                    output.append((field_event.name, load_field_data(current_field_data)))

                field_event = None
                current_field_data.clear()

            if self.processing_stage == ProcessingStage.PART:
                field_event = self._process_part()
                continue
            if self.processing_stage == ProcessingStage.PREAMBLE:
                self._process_preamble()
                continue
            if self.processing_stage == ProcessingStage.EPILOGUE:
                self._process_epilogue()
                break

        return output

    def _process_preamble(self) -> None:
        match = self.preamble_re.search(self.buffer, self.search_position)
        if match is not None:
            if match.group(1).startswith(b"--"):
                self.processing_stage = ProcessingStage.EPILOGUE
            else:
                self.processing_stage = ProcessingStage.PART

            del self.buffer[: match.end()]
            self.search_position = 0
        elif search_position := max(0, len(self.buffer) - len(self.message_boundary) - SEARCH_BUFFER_LENGTH):
            self.search_position = search_position
        else:
            self.processing_stage = ProcessingStage.EPILOGUE

    def _process_part(self) -> Optional[FieldEvent]:
        match = BLANK_LINE_RE.search(self.buffer, self.search_position)
        if match is not None:
            headers = parse_multipart_headers(self.buffer[: match.start()])
            del self.buffer[: match.end()]

            content_disposition_header = headers.get("content-disposition")
            if not content_disposition_header:
                raise ValueError("Missing Content-Disposition header")

            extra = parse_options_header(content_disposition_header)[-1]
            self.search_position = 0
            self.processing_stage = ProcessingStage.DATA
            return FieldEvent(
                headers=headers,
                name=extra.get("name", ""),
                filename=extra.get("filename", None),
            )

        self.search_position = max(0, len(self.buffer) - SEARCH_BUFFER_LENGTH)
        return None

    def _process_data(self) -> Optional[DataEvent]:
        match = self.boundary_re.search(self.buffer)
        if match is not None:
            if match.group(1).startswith(b"--"):
                self.processing_stage = ProcessingStage.EPILOGUE
            else:
                self.processing_stage = ProcessingStage.PART
            data = bytes(self.buffer[: match.start()])
            more_data = False
            del self.buffer[: match.end()]
        else:
            data_length = get_buffer_last_newline(self.buffer)
            data = bytes(self.buffer[:data_length])
            more_data = True
            del self.buffer[:data_length]
        return DataEvent(data=data, more_data=more_data) if data or not more_data else None

    def _process_epilogue(self) -> None:
        del self.buffer[:]
        self.processing_stage = ProcessingStage.COMPLETE
