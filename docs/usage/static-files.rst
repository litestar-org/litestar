=====================
Handling Static Files
=====================

Every Starlite application can serve static files from predefined locations. To
configure static file serving, either pass a single instance of |StaticFilesConfig|_ or a
list to the keyword argument of the |Starlite|_ constructor using ``static_files_config``.

For example, lets say our application is going to serve **regular files** (like JPEG or
PDF files) from the ``my_app/static`` folder & **html documents** from the
``my_app/html`` folder. Then we would like to serve the **static files** on the ``/files``
path & the **HTML files** on the ``/html`` path. To do so, we can configure the
``Starlite`` constructor like the following:

.. code-block:: python

    from starlite import Starlite, StaticFilesConfig

    app = Starlite(
        route_handlers=[...],
        static_files_config=[
            StaticFilesConfig(directories=["static"], path="/files"),
            StaticFilesConfig(directories=["html"], path="/html", html_mode=True),
        ],
    )

Matching is performed based on filenames. For example, assuming a request is attempting
to retrieve the path ``/files/file.txt``. Then the directory for the base path ``/files``
will be searched for the file ``file.txt``. If its found, the file will be sent, else a
**404 response** will be sent.

If ``html_mode`` is enabled & no specific file is requested, the application will fall
back to serving an ``index.html`` file. If no such file is found either, the application
will look for ``404.html`` file instead to render a response otherwise a
|NotFoundException|_ will be raised.

You can provide a ``name`` parameter to the ``StaticFilesConfig`` to identify the given
config & generate links to files inside folders belonging to that specific config.
``name`` should be an unique string across all static configs & route handlers.

.. code-block:: python

    from starlite import Starlite, StaticFilesConfig

    app = Starlite(
        route_handlers=[...],
        static_files_config=[
            StaticFilesConfig(
                directories=["static"], path="/some_folder/static/path", name="static"
            ),
        ],
    )

    url_path = app.url_for_static_asset("static", "files.pdf")
    # /some_folder/static/path/files.pdf

Sending Files as Attachments
============================

By default, files are sent "inline" which means they will have a
``Content-Disposition: inline`` header. To send them as attachments, use the
``send_as_attachments=True`` flag instead. This will add a
``Content-Disposition: attachment`` header instead;

.. code-block:: python

    from starlite import Starlite, StaticFilesConfig

    app = Starlite(
        route_handlers=[...],
        static_files_config=[
            StaticFilesConfig(
                directories=["static"],
                path="/some_folder/static/path",
                name="static",
                send_as_attachments=True,
            ),
        ],
    )

File System Support & Cloud Files
=================================

The ``StaticFilesConfig`` class accepts a value called ``file_system``. It can be any
class adhering to the Starlite |FileSystemProtocol|_. This protocol is similar to the
file systems defined by `fsspec <https://filesystem-spec.readthedocs.io>`_ which covers
all the major cloud providers as well as other use cases like (HTTP-based file service,
FTP & so on).

In order to use any file system, simply use ``fsspec`` or any other libraries based on
it. Or you can provide a custom implementation adhering to the ``FileSystemProtocol``.

.. |StaticFilesConfig| replace:: ``StaticFilesConfig``
.. _StaticFilesConfig: ./reference/config/6-static-files-config/#starlite.config.static_files.StaticFilesConfig

.. |Starlite| replace:: ``Starlite``
.. _Starlite: ./reference/1-app/#starlite.app.Starlite

.. |NotFoundException| replace:: ``NotFoundException``
.. _NotFoundException: ./reference/exceptions/1-http-exceptions/#starlite.exceptions.NotFoundException

.. |FileSystemProtocol| replace:: ``FileSystemProtocol``
.. _FileSystemProtocol: ./reference/types/7-file-types/#starlite.types.FileSystemProtocol
