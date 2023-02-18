Handling Static Content
=======================

Starlite is quite capable of serving static files for your application from predefined locations. It does so by either
passing an instance of :class:`StaticFilesConfig <starlite.config.StaticFilesConfig>` or a list of said instances, to
the `Starlite` application instance using the :class:`static_files_config <starlite.config.AppConfig.static_files_config>`
keyword argument.

Here is an example to showcase a Starlite application can serve ``regular files`` from the `my_app/static` folder and
markup files like HTML files from the ``my_app/html`` folder. Moreover we want our hypothetical application to serve the
static files on the ``/files`` path while the HTML content on the ``/html`` path.

.. code-block:: python

   from starlite import Starlite, StaticFilesConfig

   app = Starlite(
       route_handlers=[...],
       static_files_config=[
           StaticFilesConfig(directories=["static"], path="/files"),
           StaticFilesConfig(directories=["html"], path="/files", html_mode=True),
       ],
   )

Starlite knows which file to serve after matching the filename. For example, in context to a request attempting to
retrieve the path ``/files/file.txt``, then the directory for the base path ``/files`` will be searched for the file
``file.txt``. If found, Starlite will serve the file or a 404 response otherwise.

On the other hand, if ``html_mode`` is enabled and no specific file is requested then the application will fallback to
serving the ``index.html`` file instead. And if no such ``index.html`` file is found either, then the application will
look for a ``404.html`` instead. If in either case there is no HTML file to serve then a 404
:class:`NotFoundException <starlite.exceptions.http_exceptions.NotFoundException>` will be raised.

Its also possible to provide a ``name`` parameter to the ``StaticFilesConfig`` class for identifying and generating links
to files in folders belong to a particular config. Do note though, the value passed to the ``name`` keyword argument
should be a unique string across all static configs and route handlers.

Here's a short example code snippet showcasing the same:

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

   url_path = app.url_for_static_asset("static", "file.pdf")
   # response - "/some_folder/static/path/file.pdf"

Sending Files as Attachments
----------------------------

In a typical Starlite application, by default, files are sent "`inline`" which means the said files will have a
``Content-Disposition: inline`` header. To send them as attachments instead, the ``send_as_attachment=True`` keyword
parameter is necessary. Passing this keyword argument will add an appropriate ``Content-Disposition: attachment``
header.

Here is an example code snippet showing the same:

.. code-block:: python

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

File System Support and Cloud Files
-----------------------------------

The ``StaticFilesConfig`` class also accepts a value called :class:`file_system <starlite.config.AppConfig.file_system>`
and this value can be any class adhering to the Starlite
:class:`FileSystemProtocol <starlite.types.FileSystemProtocol>` class. The said protocol is similar to the file systems
defined by `fsspec <https://filesystem-spec.readthedocs.io>`_ which covers all major cloud providers and a wide range of
other use cases (like HTTP-based file serves, FTP and more).

In order to use any file-system with your Starlite application, simple use ``fsspec`` or one of the libraries based on
it. Or you can also provide a custom implementation adhering to the ``FileSystemProtocol`` class.

.. TODO: Example(s)?
