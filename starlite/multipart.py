"""The contents of this file were adapted from sanic.

MIT License

Copyright (c) 2016-present Sanic Community

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import re
from collections import defaultdict
from email.utils import decode_rfc2231
from typing import Any, DefaultDict, Dict, List, Tuple
from urllib.parse import unquote

from msgspec import DecodeError

from starlite.datastructures.upload_file import UploadFile
from starlite.utils.serialization import decode_json

_token, _quoted = r"([\w!#$%&'*+\-.^_`|~]+)", r'"([^"]*)"'
_param = re.compile(rf";\s*{_token}=(?:{_token}|{_quoted})", re.ASCII)
_firefox_quote_escape = re.compile(r'\\"(?!; |\s*$)')


def parse_content_header(value: str) -> Tuple[str, Dict[str, str]]:
    """Parse content-type and content-disposition header values.

    Args:
        value: A header string value to parse.

    Returns:
        A tuple containing the normalized header string and a dictionary of parameters.
    """
    value = _firefox_quote_escape.sub("%22", value)
    pos = value.find(";")
    if pos == -1:
        options: Dict[str, str] = {}
    else:
        options = {
            m.group(1).lower(): m.group(2) or m.group(3).replace("%22", '"') for m in _param.finditer(value[pos:])
        }
        value = value[:pos]
    return value.strip().lower(), options


def parse_multipart_form(body: bytes, boundary: bytes) -> Dict[str, Any]:
    """Parse multipart form data.

    Args:
        body: Body of the request.
        boundary: Boundary of the multipart message.

    Returns:
        A dictionary of parsed results.
    """

    fields: DefaultDict[str, List[Any]] = defaultdict(list)

    if body and boundary:

        form_parts = body.split(boundary)
        for form_part in form_parts[1:-1]:
            file_name = None
            content_type = "text/plain"
            content_charset = "utf-8"
            field_name = None
            line_index = 2
            line_end_index = 0
            headers: List[Tuple[str, str]] = []

            while line_end_index != -1:
                line_end_index = form_part.find(b"\r\n", line_index)
                form_line = form_part[line_index:line_end_index].decode("utf-8")

                if not form_line:
                    break

                line_index = line_end_index + 2
                colon_index = form_line.index(":")
                current_idx = colon_index + 2
                form_header_field = form_line[0:colon_index].lower()
                form_header_value, form_parameters = parse_content_header(form_line[current_idx:])

                if form_header_field == "content-disposition":
                    field_name = form_parameters.get("name")
                    file_name = form_parameters.get("filename")

                    if file_name is None and (filename_with_asterisk := form_parameters.get("filename*")):
                        encoding, _, value = decode_rfc2231(filename_with_asterisk)
                        file_name = unquote(value, encoding=encoding or content_charset)

                elif form_header_field == "content-type":
                    content_type = form_header_value
                    content_charset = form_parameters.get("charset", "utf-8")
                headers.append((form_header_field, form_header_value))

            if field_name:
                post_data = form_part[line_index:-4].lstrip(b"\r\n")
                if file_name:
                    form_file = UploadFile(
                        content_type=content_type, filename=file_name, file_data=post_data, headers=dict(headers)
                    )
                    fields[field_name].append(form_file)
                else:
                    try:
                        fields[field_name].append(decode_json(post_data))
                    except DecodeError:
                        fields[field_name].append(post_data.decode(content_charset))

    return {k: v if len(v) > 1 else v[0] for k, v in fields.items()}
