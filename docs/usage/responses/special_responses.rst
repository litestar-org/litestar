Special Responses
=================

File Responses
--------------

File responses send a file:

.. code-block:: python

   from pathlib import Path
   from litestar import get
   from litestar.response import File


   @get(path="/file-download")
   def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )

Where ``path`` is the path of the file to be sent and ``filename`` an optional filename to set
in the response `Content-Disposition <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition>`_
attachment.


Media types
+++++++++++

If ``filename`` is provided, Litestar will try to guess the MIME type, otherwise fall
back to ``application/octet-stream``. If the type cannot be inferred via the file name,
you can set it manually via ``media_type``

For example:

.. code-block:: python

   from pathlib import Path
   from litestar import get
   from litestar.response import File


   @get(path="/file-download", media_type="application/pdf")
   def handle_file_download() -> File:
       return File(
           path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
           filename="report.pdf",
       )


Streaming
+++++++++

File responses are streamed or sent in one chunk. This depends on the file's size and
the ``chunk_size`` set, which defaults to 1 MB. If the file exceeds ``chunk_size``, it
will be streamed.


File systems
++++++++++++

:class:`~litestar.response.File` supports Litestar's *file system protocol and registry*.
If no file system is passed explicitly, files will be sent using the registry's default
file system, which itself defaults to
:class:`~litestar.file_system.BaseLocalFileSystem`\ , sending files from disk.
In addition to Litestar's own file system protocol, all
`fsspec <https://filesystem-spec.readthedocs.io/en/latest/>`_ file systems are
supported.

.. literalinclude:: /examples/responses/file_response_fs.py
    :language: python
    :caption: Sending files from S3


.. literalinclude:: /examples/responses/file_response_fs_registry.py
    :language: python
    :caption: Sending files from S3 by using the registry


Streaming Responses
-------------------

To return a streaming response use the :class:`Stream <.response.Stream>` class. The class
receives a single positional arg, that must be an iterator delivering the stream:

.. literalinclude:: /examples/responses/streaming_responses.py
    :language: python


.. note::

    You can use different kinds of values for the iterator. It can be a callable returning a sync or async generator,
    a generator itself, a sync or async iterator class, or an instance of a sync or async iterator class.


Server Sent Event Responses
---------------------------

To send `server-sent-events` or SSEs to the frontend, use the :class:`ServerSentEvent <.response.ServerSentEvent>`
class. The class receives a content arg. You can additionally specify ``event_type``, which is the
name of the event as declared in the browser, the ``event_id``, which sets the event source property, ``comment_message``,
which is used in for sending pings, and ``retry_duration``, which dictates the duration for retrying.

.. literalinclude:: /examples/responses/sse_responses.py
    :language: python


.. note::

    You can use different kinds of values for the iterator. It can be a callable returning a sync or async generator,
    a generator itself, a sync or async iterator class, or an instance of a sync or async iterator class.

In your iterator function you can yield integers, strings or bytes, the message sent in that case will have ``message``
as the ``event_type`` if the ServerSentEvent has no ``event_type`` set, otherwise it will use the ``event_type``
specified, and the data will be the yielded value.

If you want to send a different event type, you can use a dictionary with the keys ``event_type`` and ``data`` or the :class:`ServerSentEventMessage <.response.ServerSentEventMessage>` class.

.. note::

    You can further customize all the sse parameters, add comments, and set the retry duration by using the :class:`ServerSentEvent <.response.ServerSentEvent>` class directly or by using the :class:`ServerSentEventMessage <.response.ServerSentEventMessage>` or dictionaries with the appropriate keys.

To prevent reverse proxies or clients from closing idle SSE connections, use the ``ping_interval`` parameter:

.. code-block:: python

    @get("/stream")
    async def stream_handler() -> ServerSentEvent:
        async def generator():
            while True:
                data = await get_data()
                yield data

        return ServerSentEvent(generator(), ping_interval=15)

The ``ping_interval`` value is in **seconds**. This sends an SSE comment (``: ping``) every 15 seconds to keep the
connection alive. SSE comments are invisible to ``EventSource`` clients and will not trigger message events.
Pings begin after the first interval elapses (no immediate ping on connect).

.. tip::

    Common values are 15–30 seconds, depending on your reverse proxy's idle timeout
    (e.g., nginx defaults to 60 seconds, Telegram Mini Apps time out after 60 seconds).


Template Responses
------------------

Template responses are used to render templates into HTML. To use a template response you must first
:ref:`register a template engine <usage/templating:registering a template engine>` on the application level. Once an
engine is in place, you can use a template response like so:

.. code-block:: python

   from litestar import Request, get
   from litestar.response import Template


   @get(path="/info")
   def info(request: Request) -> Template:
       return Template(template_name="info.html", context={"user": request.user})

In the above example, :class:`Template <.response.Template>` is passed the template name, which is a
path like value, and a context dictionary that maps string keys into values that will be rendered in the template.

Custom Responses
----------------

While Litestar supports the serialization of many types by default, sometimes you want to return something that's not
supported. In those cases it's convenient to make use of a custom response class.

The example below illustrates how to deal with :class:`MultiDict <.datastructures.MultiDict>`
instances.

.. literalinclude:: /examples/responses/custom_responses.py
    :language: python

.. admonition:: Layered architecture
    :class: seealso

    Response classes are part of Litestar's layered architecture, which means you can
    set a response class on every layer of the application. If you have set a response
    class on multiple layers, the layer closest to the route handler will take precedence.

    You can read more about this here: :ref:`usage/applications:layered architecture`
