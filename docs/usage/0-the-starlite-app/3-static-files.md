# Static Files

Static files are served by the app from predefined locations. To configure static file serving, either pass an
instance of [`StaticFilesConfig`][starlite.config.static_files.StaticFilesConfig] or a list
thereof to the [Starlite constructor][starlite.app.Starlite] using the `static_files_config` kwarg.

For example, lets say our Starlite app is going to serve **regular files** from the `my_app/static` folder and **html
documents** from the `my_app/html` folder, and we would like to serve the **static files** on the `/files` path,
and the **html files** on the `/html` path:

```python
from starlite import Starlite, StaticFilesConfig

app = Starlite(
    route_handlers=[...],
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/files"),
        StaticFilesConfig(directories=["html"], path="/html", html_mode=True),
    ],
)
```


Matching is done based on filename, for example, assume we have a request that is trying to retrieve the path
`/files/file.txt`, the **directory for the base path** `/files` **will be searched** for the file `file.txt`. If it is
found, the file will be sent, otherwise a **404 response** will be sent.

If `html_mode` is enabled and no specific file is requested, the application will fall back to serving `index.html`. If
no file is found the application will look for a `404.html` file in order to render a response, otherwise a 404
[`NotFoundException`][starlite.exceptions.NotFoundException] will be returned.

You can provide a `name` parameter to `StaticFilesConfig` to identify the given config and generate links to files in
folders belonging to that config. `name` should be a unique string across all static configs and
[route handlers](../2-route-handlers/4-route-handler-indexing.md).

```python
from starlite import Starlite, StaticFilesConfig

app = Starlite(
    route_handlers=[...],
    static_files_config=[
        StaticFilesConfig(
            directories=["static"], path="/some_folder/static/path", name="static"
        ),
    ],
)

url_path = app.url_for_static_asset("static", "file.pdf")
# /some_folder/static/path/file.pdf
```


## Sending files as attachments

By default, files are sent "inline", meaning they will have a `Content-Disposition: inline` header.
To send them as attachments, use the `send_as_attachment=True` flag, which will add a
`Content-Disposition: attachment` header:

```python
from starlite import Starlite, StaticFilesConfig

app = Starlite(
    route_handlers=[...],
    static_files_config=[
        StaticFilesConfig(
            directories=["static"],
            path="/some_folder/static/path",
            name="static",
            send_as_attachment=True,
        ),
    ],
)
```

## File System Support and Cloud Files

The [`StaticFilesConfig`][starlite.config.static_files.StaticFilesConfig] class accepts a value called `file_system`,
which can be any class adhering to the Starlite [`FileSystemProtocol`][starlite.types.FileSystemProtocol].

This protocol is similar to the file systems defined by [fsspec](https://filesystem-spec.readthedocs.io/en/latest/),
which cover all major cloud providers and a wide range of other use cases (e.g. HTTP based file service, `ftp` etc.).

In order to use any file system, simply use [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) or one of
the libraries based upon it, or provide a custom implementation adhering to the
[`FileSystemProtocol`][starlite.types.FileSystemProtocol].
