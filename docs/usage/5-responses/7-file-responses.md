# File Responses

File responses send a file:

```python
from pathlib import Path
from starlite import get
from starlite.datastructures import File


@get(path="/file-download")
def handle_file_download() -> File:
    return File(
        path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
        filename="repost.pdf",
    )
```

The File class expects two kwargs:

- `path`: path of the file to download.
- `filename`: the filename to set in the
  response [Content-Disposition](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition)
  attachment.

!!! important
    When a route handler's return value is annotated with `File`, the default `media_type` for the
    route_handler is switched from `MediaType.JSON` to `MediaType.TEXT` (i.e. "text/plain"). If the file being sent has
    an [IANA media type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types), you should set it as
    the value for `media_type` instead.

For example:

```python
from pathlib import Path
from starlite import get
from starlite.datastructures import File


@get(path="/file-download", media_type="application/pdf")
def handle_file_download() -> File:
    return File(
        path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
        filename="repost.pdf",
    )
```

## The File Class

`File` is a container class used to generate file responses and their respective OpenAPI documentation.
See the [API Reference][starlite.datastructures.File] for full details on the `File` class and the kwargs it accepts.
