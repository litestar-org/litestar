HTMX
====

Litestar `HTMX <https://htmx.org>`_ integration.

HTMX is a JavaScript library that gives you access to AJAX, CSS Transitions, WebSockets and Server Sent Events directly in HTML, using attributes, so you can build modern user interfaces with the simplicity and power of hypertext.

This section assumes that you have prior knowledge of HTMX.
If you want to learn HTMX, we recommend consulting their `official tutorial <https://htmx.org/docs>`_.


HTMXPlugin
------------

a Litestar plugin ``HTMXPlugin`` is available to easily configure the default request class for all Litestar routes.

It can be installed via the ``litestar[htmx]`` package extra.

.. code-block:: python

    from litestar.plugins.htmx import HTMXPlugin
    from litestar import Litestar

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from pathlib import Path

    app = Litestar(
        route_handlers=[get_form],
        debug=True,
        plugins=[HTMXPlugin()],
        template_config=TemplateConfig(
            directory=Path("litestar_htmx/templates"),
            engine=JinjaTemplateEngine,
        ),
    )

See :class:`~litestar.plugins.htmx.HTMXDetails` for a full list of
available properties.

HTMXRequest
------------

A special :class:`~litestar.connection.Request` class, providing interaction with the
HTMX client.  You can configure this globally by using the ``HTMXPlugin`` or by setting the `request_class` setting on any route, controller, router, or application.

.. code-block:: python

    from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
    from litestar import get, Litestar
    from litestar.response import Template

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from pathlib import Path


    @get(path="/form")
    def get_form(request: HTMXRequest) -> Template:
        if request.htmx:  # if request has "HX-Request" header, then
            print(request.htmx)  # HTMXDetails instance
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

See :class:`~litestar.plugins.htmx.HTMXDetails` for a full list of
available properties.


HTMX Response Classes
---------------------


HTMXTemplate Response Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most common  use-case for HTMX to render an html page or html snippet. Litestar makes this easy by providing
an :class:`~litestar.plugins.htmx.HTMXTemplate` response:

.. code-block:: python

    from litestar.plugins.htmx import HTMXTemplate
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
    - Return type is litestar's ``Template`` and not ``HTMXTemplate``.
    - ``trigger_event``, ``params``, and ``after`` parameters are linked to one another.
    - If you are triggering an event then ``after`` is required and it must be one of ``receive``, ``settle``, or ``swap``.

HTMX provides two types of responses - one that doesn't allow changes to the DOM and one that does.
Litestar supports both of these:

1 - Responses that don't make any changes to DOM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :class:`~litestar.plugins.htmx.HXStopPolling` to stop polling for a response.

.. code-block:: python

    @get("/")
    def handler() -> HXStopPolling:
        ...
        return HXStopPolling()

Use :class:`~litestar.plugins.htmx.ClientRedirect` to redirect with a page reload.

.. code-block:: python

    @get("/")
    def handler() -> ClientRedirect:
        ...
        return ClientRedirect(redirect_to="/contact-us")

Use :class:`~litestar.plugins.htmx.ClientRefresh` to force a full page refresh.

.. code-block:: python

    @get("/")
    def handler() -> ClientRefresh:
        ...
        return ClientRefresh()

2 - Responses that may change DOM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :class:`~litestar.plugins.htmx.HXLocation` to redirect to a new location without page reload.

.. note:: This class provides the ability to change ``target``, ``swapping`` method, the sent ``values``, and the ``headers``.

.. code-block:: python

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
            hx_headers={"attr": "val"},  # headers to pass to HTMX.
            values={"val": "one"},
        )  # values to submit with response.

Use :class:`~litestar.plugins.htmx.PushUrl` to carry a response and push a url to the browser, optionally updating the ``history`` stack.

.. note:: If the value for ``push_url`` is set to ``False`` it will prevent updating browser history.

.. code-block:: python

    @get("/about")
    def handler() -> PushUrl:
        ...
        return PushUrl(content="Success!", push_url="/about")

Use :class:`~litestar.plugins.htmx.ReplaceUrl` to carry a response and replace the url in the browser's ``location`` bar.

.. note:: If the value to ``replace_url`` is set to ``False`` it will prevent updating the browser's location.

.. code-block:: python

    @get("/contact-us")
    def handler() -> ReplaceUrl:
        ...
        return ReplaceUrl(content="Success!", replace_url="/contact-us")

Use :class:`~litestar.plugins.htmx.Reswap` to carry a response with a possible swap.

.. code-block:: python

    @get("/contact-us")
    def handler() -> Reswap:
        ...
        return Reswap(content="Success!", method="beforebegin")

Use :class:`~litestar.plugins.htmx.Retarget` to carry a response and change the target element.

.. code-block:: python

    @get("/contact-us")
    def handler() -> Retarget:
        ...
        return Retarget(content="Success!", target="#new-target")

Use :class:`~litestar.plugins.htmx.TriggerEvent` to carry a response and trigger an event.

.. code-block:: python

    @get("/contact-us")
    def handler() -> TriggerEvent:
        ...
        return TriggerEvent(
            content="Success!",
            name="showMessage",
            params={"attr": "value"},
            after="receive",  # possible values 'receive', 'settle', and 'swap'
        )
