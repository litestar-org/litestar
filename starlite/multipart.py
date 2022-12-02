import re
from collections import defaultdict
from email.utils import decode_rfc2231
from io import BytesIO
from json import loads
from typing import Dict, Union, Tuple, Any
from urllib.parse import unquote

from orjson import JSONDecodeError

from starlite.datastructures.upload_file import UploadFile

_token, _quoted = r"([\w!#$%&'*+\-.^_`|~]+)", r'"([^"]*)"'
_param = re.compile(rf";\s*{_token}=(?:{_token}|{_quoted})", re.ASCII)
_firefox_quote_escape = re.compile(r'\\"(?!; |\s*$)')


def parse_content_header(value: str) -> Tuple[str, Dict[str, Union[int, str]]]:
    """Parse content-type and content-disposition header values.
    E.g. 'form-data; name=upload; filename=\"file.txt\"' to
    ('form-data', {'name': 'upload', 'filename': 'file.txt'})
    Mostly identical to cgi.parse_header and werkzeug.parse_options_header
    but runs faster and handles special characters better. Unescapes quotes.
    """
    value = _firefox_quote_escape.sub("%22", value)
    pos = value.find(";")
    if pos == -1:
        options: Dict[str, Union[int, str]] = {}
    else:
        options = {
            m.group(1).lower(): m.group(2) or m.group(3).replace("%22", '"') for m in _param.finditer(value[pos:])
        }
        value = value[:pos]
    return value.strip().lower(), options


def parse_multipart_form(body: bytes, boundary: bytes) -> Dict[str, Any]:
    """
    Parse a request body and returns fields and files
    :param body: bytes request body
    :param boundary: bytes multipart boundary
    :return: fields (RequestParameters), files (RequestParameters)
    """

    fields = defaultdict(list)

    form_parts = body.split(boundary)
    for form_part in form_parts[1:-1]:
        file_name = None
        content_type = "text/plain"
        content_charset = "utf-8"
        field_name = None
        line_index = 2
        line_end_index = 0
        while not line_end_index == -1:
            line_end_index = form_part.find(b"\r\n", line_index)
            form_line = form_part[line_index:line_end_index].decode("utf-8")
            line_index = line_end_index + 2

            if not form_line:
                break

            colon_index = form_line.index(":")
            idx = colon_index + 2
            form_header_field = form_line[0:colon_index].lower()
            form_header_value, form_parameters = parse_content_header(form_line[idx:])

            if form_header_field == "content-disposition":
                field_name = form_parameters.get("name")
                file_name = form_parameters.get("filename")

                # non-ASCII filenames in RFC2231, "filename*" format
                if file_name is None and form_parameters.get("filename*"):
                    encoding, _, value = decode_rfc2231(form_parameters["filename*"])
                    file_name = unquote(value, encoding=encoding)
            elif form_header_field == "content-type":
                content_type = form_header_value
                content_charset = form_parameters.get("charset", "utf-8")

        if field_name:
            post_data = form_part[line_index:-4]
            if file_name is None:
                try:
                    fields[field_name].append(loads(post_data))
                except JSONDecodeError:
                    fields[field_name].append(post_data.decode(content_charset))
            else:
                form_file = UploadFile(content_type=content_type, filename=file_name, file=BytesIO(post_data))
                fields[field_name].append(form_file)

    return {k: v if len(v) > 1 else v[0] for k, v in fields.items()}
