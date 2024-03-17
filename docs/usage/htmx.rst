HTMX
====

`HTMX <https://htmx.org/>`_ gives you access to AJAX, CSS Transitions, WebSockets and Server Sent Events directly in
HTML, using attributes, so you can build modern user interfaces with the simplicity and power of hypertext.
HTMX has no outside dependencies outside of a vanilla JavaScript file referenced in your HTML ``<head>`` section.

Check out the `HTMX documentation <https://htmx.org/docs>`_, or community repositories like
`awesome-python-htmx <https://github.com/PyHAT-stack/awesome-python-htmx>`_ for more information.

:class:`~litestar.contrib.htmx.request.HTMXRequest`
---------------------------------------------------

A special :class:`~litestar.connection.Request` class, providing interaction with the HTMX client.

.. code-block:: python
    :caption: Example of using HTMXRequest

    from litestar.contrib.htmx.request import HTMXRequest
    from litestar.contrib.htmx.response import HTMXTemplate
    from litestar import get, Litestar
    from litestar.response import Template

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from pathlib import Path


    @get(path="/form")
    def get_form(request: HTMXRequest) -> Template:
        htmx = request.htmx  #  if true will return HTMXDetails class object
        if htmx:
            print(htmx.current_url)
        # OR
        if request.htmx:
            print(request.htmx.current_url)
        return HTMXTemplate(template_name="partial.html", context=context, push_url="/form")


    app = Litestar(
        route_handlers=[get_form],
        debug=True,
        request_class=HTMXRequest,
        template_config=TemplateConfig(
            directory=Path("litestar_htmx/templates"),
            engine=JinjaTemplateEngine,
        ),
    )

See :class:`HTMXDetails <litestar.contrib.htmx.request.HTMXDetails>` for a full list of available properties.

HTMX Response Classes
---------------------

:class:`HTMXTemplate <litestar.contrib.htmx.response.HTMXTemplate>` Response Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most common use case for ``htmx`` to render an html page or html snippet. Litestar makes this easy by providing
an :class:`HTMXTemplate <litestar.contrib.htmx.response.HTMXTemplate>` response:

.. code-block:: python
    :caption: Example of using a :class:`HTMXTemplate <litestar.contrib.htmx.response.HTMXTemplate>` response

    from litestar.contrib.htmx.response import HTMXTemplate
    from litestar.response import Template


    @get(path="/form")
    def get_form(
        request: HTMXRequest,
    ) -> Template:  # Return type is Template and not HTMXTemplate.
        ...
        return HTMXTemplate(
            template_name="partial.html",
            context=context,
            # Optional parameters
            push_url="/form",  # update browser history
            re_swap="outerHTML",  # change swapping method
            re_target="#new-target",  # change target element
            trigger_event="showMessage",  # trigger event name
            params={"alert": "Confirm your Choice."},  # parameter to pass to the event
            after="receive",  #  when to trigger event,
            # possible values 'receive', 'settle', and 'swap'
        )

.. note::
    - Return type is litestar's :class:`~litestar.response.template.Template` and not
      :class:`HTMXTemplate <litestar.contrib.htmx.response.HTMXTemplate>`.
    - ``trigger_event``, ``params``, and ``after parameters`` are linked to one another.
    - If you are triggering an event then ``after`` is required and it must be one of ``receive``, ``settle``, or ``swap``.

HTMX provides two types of responses - one that does not allow changes to the DOM and one that does.
Litestar supports both of these:

1 - Responses that do not make any changes to DOM.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`HXStopPolling <litestar.contrib.htmx.response.HXStopPolling>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`HXStopPolling <litestar.contrib.htmx.response.HXStopPolling>` to stop polling for a response.

.. code-block:: python
    :caption: Example of using :class:`HXStopPolling <litestar.contrib.htmx.response.HXStopPolling>`

    @get("/")
    def handler() -> HXStopPolling:
        ...
        return HXStopPolling()

:class:`ClientRedirect  <litestar.contrib.htmx.response.ClientRedirect>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`ClientRedirect  <litestar.contrib.htmx.response.ClientRedirect>` to redirect with a page reload.

.. code-block:: python
    :caption: Example of using :class:`ClientRedirect  <litestar.contrib.htmx.response.ClientRedirect>`

    @get("/")
    def handler() -> ClientRedirect:
        ...
        return ClientRedirect(redirect_to="/contact-us")

:class:`ClientRefresh  <litestar.contrib.htmx.response.ClientRefresh>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`ClientRefresh  <litestar.contrib.htmx.response.ClientRefresh>` to force a full page refresh.

.. code-block:: python
    :caption: Example of using :class:`ClientRefresh  <litestar.contrib.htmx.response.ClientRefresh>`

    @get("/")
    def handler() -> ClientRefresh:
        ...
        return ClientRefresh()

2 - Responses that may change DOM.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`HXLocation <litestar.contrib.htmx.response.HXLocation>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`HXLocation <litestar.contrib.htmx.response.HXLocation>` to redirect to a new location without page reload.

.. note:: This class provides the ability to change ``target``, ``swapping`` method, the sent ``values``,
    and the ``headers``.

.. code-block:: python
    :caption: Example of using :class:`HXLocation <litestar.contrib.htmx.response.HXLocation>`

    @get("/about")
    def handler() -> HXLocation:
        ...
        return HXLocation(
            redirect_to="/contact-us",
            # Optional parameters
            source,  # the source element of the request.
            event,  # an event that "triggered" the request.
            target="#target",  # element id to target to.
            swap="outerHTML",  # swapping method to use.
            hx_headers={"attr": "val"},  # headers to pass to htmx.
            values={"val": "one"},
        )  # values to submit with response.

:class:`PushUrl <litestar.contrib.htmx.response.PushUrl>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`PushUrl <litestar.contrib.htmx.response.PushUrl>` to carry a response and push a url to the browser,
optionally updating the ``history`` stack.

.. note:: If the value for ``push_url`` is set to ``False`` it will __prevent__ updating browser history.

.. code-block:: python
    :caption: Example of using :class:`PushUrl <litestar.contrib.htmx.response.PushUrl>`

    @get("/about")
    def handler() -> PushUrl:
        ...
        return PushUrl(content="Success!", push_url="/about")

:class:`ReplaceUrl <litestar.contrib.htmx.response.ReplaceUrl>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`ReplaceUrl <litestar.contrib.htmx.response.ReplaceUrl>` to carry a response and replace the url in the
browser's ``location`` bar.

.. note:: If the value to ``replace_url`` is set to ``False`` it will prevent it updating the browser location bar.

.. code-block:: python
    :caption: Example of using :class:`ReplaceUrl <litestar.contrib.htmx.response.ReplaceUrl>`

    @get("/contact-us")
    def handler() -> ReplaceUrl:
        ...
        return ReplaceUrl(content="Success!", replace_url="/contact-us")

:class:`Reswap <litestar.contrib.htmx.response.Reswap>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`Reswap <litestar.contrib.htmx.response.Reswap>` to carry a response perhaps a swap

.. code-block:: python
    :caption: Example of using :class:`Reswap <litestar.contrib.htmx.response.Reswap>`

    @get("/contact-us")
    def handler() -> Reswap:
        ...
        return Reswap(content="Success!", method="beforebegin")

:class:`Retarget <litestar.contrib.htmx.response.Retarget>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`Retarget <litestar.contrib.htmx.response.Retarget>` to carry a response and change the target element.

.. code-block:: python
    :caption: Example of using :class:`Retarget <litestar.contrib.htmx.response.Retarget>`

    @get("/contact-us")
    def handler() -> Retarget:
        ...
        return Retarget(content="Success!", target="#new-target")

:class:`TriggerEvent <litestar.contrib.htmx.response.TriggerEvent>`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use :class:`TriggerEvent <litestar.contrib.htmx.response.TriggerEvent>` to carry a response and trigger an event.

.. code-block:: python
    :caption: Example of using :class:`TriggerEvent <litestar.contrib.htmx.response.TriggerEvent>`

    @get("/contact-us")
    def handler() -> TriggerEvent:
        ...
        return TriggerEvent(
            content="Success!",
            name="showMessage",
            params={"attr": "value"},
            after="receive",  # possible values 'receive', 'settle', and 'swap'
        )
