import re
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote_to_bytes

from starlite.datastructures import Headers, UploadFile


@dataclass
class PreambleEvent:
    __slots__ = ("data",)

    data: bytes


@dataclass
class FieldEvent:
    __slots__ = (
        "name",
        "headers",
    )

    name: str
    headers: Dict[str, str]


@dataclass
class FileEvent:
    __slots__ = (
        "name",
        "headers",
        "filename",
    )

    name: str
    filename: str
    headers: Dict[str, str]


@dataclass
class DataEvent:
    __slots__ = (
        "data",
        "more_data",
    )

    data: bytes
    more_data: bool


@dataclass
class EpilogueEvent:
    __slots__ = ("data",)

    data: bytes


MultipartMessageEvent = Union[PreambleEvent, FileEvent, FieldEvent, DataEvent, EpilogueEvent]


def get_buffer_last_newline(buffer: bytearray) -> int:
    """Returns the position of the last new line break. Handles malformed new line formatting.

    Notes:
        - This function makes use of rindex specifically because -1 is also used. Hence, using find cannot work.
        -  Multipart line breaks MUST be CRLF (\r\n) by RFC-7578, except that many implementations break this and either
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


def parse_headers(data: bytes, charset: str = "utf-8") -> Dict[str, str]:
    """Given a message byte string, parse the headers component of it and return a dictionary of normalized key/value
    pairs.

    Args:
        data: A byte string.
        charset: Encoding charset used

    Returns:
        A string / string dictionary of parsed values.
    """
    data = RFC2231_HEADER_CONTINUATION_RE.sub(b" ", data)

    headers: Dict[str, str] = {}
    for name, value in [line.decode(charset).split(":", 1) for line in data.splitlines() if line.strip() != b""]:
        headers[name.strip().lower()] = value.strip()

    return headers


def unquote_header_value(value: str, is_filename: bool = False) -> str:
    """Unquotes a header value. This does not use the real unquoting but what browsers are actually using for quoting.

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
    """Parses a 'Content-Type' or 'Content-Disposition' header, returning the header value and any options as a
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


class RequestEntityTooLarge(Exception):
    pass


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
    PREAMBLE = 1
    PART = 2
    DATA = 3
    EPILOGUE = 4
    COMPLETE = 5


class MultipartDecoder:
    __slots__ = (
        "boundary_re",
        "buffer",
        "charset",
        "max_file_size",
        "message_boundary",
        "preamble_re",
        "processing_stage",
        "search_position",
    )

    def __init__(
        self, message_boundary: Union[bytes, str], max_file_size: Optional[int] = None, charset: str = "utf-8"
    ) -> None:
        """A decoder for multipart messages.

        Args:
            message_boundary: The message message_boundary as specified by [RFC7578][https://www.rfc-editor.org/rfc/rfc7578]
            max_file_size: Maximum number of bytes allowed for the message.
        """
        self.buffer = bytearray()
        self.charset = charset
        self.max_file_size = max_file_size
        self.processing_stage = ProcessingStage.PREAMBLE
        self.search_position = 0
        self.message_boundary = (
            message_boundary if isinstance(message_boundary, bytes) else message_boundary.encode("latin-1")
        )

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

    def __call__(self, data: bytes) -> None:
        if data:
            if self.max_file_size is not None and len(self.buffer) + len(data) > self.max_file_size:
                raise RequestEntityTooLarge()
            self.buffer.extend(data)

    def _process_preamble(self) -> Optional[PreambleEvent]:
        event: Optional[PreambleEvent] = None
        match = self.preamble_re.search(self.buffer, self.search_position)
        if match is not None:
            if match.group(1).startswith(b"--"):
                self.processing_stage = ProcessingStage.EPILOGUE
            else:
                self.processing_stage = ProcessingStage.PART

            data = bytes(self.buffer[: match.start()])
            del self.buffer[: match.end()]
            event = PreambleEvent(data=data)
        if event:
            self.search_position = 0
        else:
            self.search_position = max(0, len(self.buffer) - len(self.message_boundary) - SEARCH_BUFFER_LENGTH)
        return event

    def _process_part(self) -> Optional[Union[FileEvent, FieldEvent]]:
        event: Optional[Union[FileEvent, FieldEvent]] = None
        match = BLANK_LINE_RE.search(self.buffer, self.search_position)
        if match is not None:
            headers = parse_headers(self.buffer[: match.start()], charset=self.charset)
            del self.buffer[: match.end()]

            content_disposition_header = headers.get("content-disposition")
            if not content_disposition_header:
                raise ValueError("Missing Content-Disposition header")

            _, extra = parse_options_header(content_disposition_header)
            if "filename" in extra:
                event = FileEvent(
                    filename=extra["filename"],
                    headers=headers,
                    name=extra.get("name", ""),
                )
            else:
                event = FieldEvent(
                    headers=headers,
                    name=extra.get("name", ""),
                )
        if event:
            self.search_position = 0
            self.processing_stage = ProcessingStage.DATA
        else:
            self.search_position = max(0, len(self.buffer) - SEARCH_BUFFER_LENGTH)
        return event

    def _process_data(self) -> Optional[DataEvent]:
        match = self.boundary_re.search(self.buffer) if self.buffer.find(b"--" + self.message_boundary) != -1 else None
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

    def _process_epilogue(self) -> EpilogueEvent:
        event = EpilogueEvent(data=bytes(self.buffer))  # noqa: R504
        del self.buffer[:]
        self.processing_stage = ProcessingStage.COMPLETE
        return event

    def next_event(self) -> Optional[MultipartMessageEvent]:
        """Processes the data according the parser's processing_stage. The processing_stage is updated according to the
        parser's processing_stage machine logic. Thus calling this method updates the processing_stage as well.

        Returns:
            An optional event instance, depending on the processing_stage of the message processing.
        """
        if self.processing_stage == ProcessingStage.PREAMBLE:
            return self._process_preamble()
        if self.processing_stage == ProcessingStage.PART:
            return self._process_part()
        if self.processing_stage == ProcessingStage.DATA:
            return self._process_data()
        if self.processing_stage == ProcessingStage.EPILOGUE:
            return self._process_epilogue()
        return None


class MultipartFormDataParser:
    __slots__ = ("headers", "stream", "decoder", "charset")

    def __init__(
        self,
        headers: Dict[str, str],
        stream: AsyncGenerator[bytes, None],
        max_file_size: Optional[int],
        charset: str = "utf-8",
    ) -> None:
        """Parses multipart/formdata.

        Args:
            headers: A mapping of headers.
            stream: An async generator yielding a stream.
            max_file_size: Max file size allowed.
            charset: Charset used to encode the data.
        """
        self.headers = {k.lower(): v for k, v in headers.items()}
        _, options = parse_options_header(self.headers.get("content-type", ""))
        self.stream = stream
        self.charset = options.get("charset", charset)
        self.decoder = MultipartDecoder(
            message_boundary=options.get("boundary", ""), max_file_size=max_file_size, charset=charset
        )

    async def parse(self) -> List[Tuple[str, Union[str, UploadFile]]]:
        """Parses a chunk into a list of items.

        Returns:
            A list of tuples, each containing the field name and its value - either a string or an upload file datum.
        """
        items: List[Tuple[str, Union[str, UploadFile]]] = []

        field_name = ""
        data = bytearray()
        upload_file: Optional[UploadFile] = None
        while True:
            event = self.decoder.next_event()
            if event is None or isinstance(event, EpilogueEvent):
                break
            if isinstance(event, FieldEvent):
                field_name = event.name
            elif isinstance(event, FileEvent):
                field_name = event.name
                upload_file = UploadFile(
                    filename=event.filename,
                    content_type=event.headers.get("content-type", ""),
                    headers=Headers(event.headers),
                )
            elif isinstance(event, DataEvent):
                if upload_file:
                    await upload_file.write(event.data)
                    if not event.more_data:
                        await upload_file.seek(0)
                        items.append((field_name, upload_file))
                        upload_file = None
                        data.clear()
                else:
                    data.extend(event.data)
                    if not event.more_data:
                        try:
                            items.append((field_name, data.decode(self.charset)))
                        except UnicodeDecodeError:
                            items.append((field_name, data.decode("latin-1")))
                        data.clear()
        return items

    async def __call__(self) -> List[Tuple[str, Union[str, UploadFile]]]:
        """Asynchronously parses the stream data.

        Returns:
            A list of tuples, each containing the field name and its value - either a string or an upload file datum.
        """
        async for chunk in self.stream:
            self.decoder(chunk)
        return await self.parse()
