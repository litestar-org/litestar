HTMX Request Class
=====================

This class reads headers sent by htmx client and saves it in convenient properties. Also it is extended from starlite Request class so,
whenever you are working with HTMX library you can access all htmx headers along with Starlite Request methods and properties.

.. code-block:: python

    from starlite.contrib.htmx.request import HTMXRequest
    from starlite.contrib.htmx.response import HTMXTemplate


    @get(path="/form")
    def get_form(request: HTMXRequest) -> Template:
        htmx = request.htmx  #  if true will return HtmxDetails class object
        if htmx:
            print(htmx.current_url)
        # OR
        if request.htmx:
            print(request.htmx.current_url)
        return HTMXTemplate(name="partial.html", context=context, push_url="/form")

Full list of headers that :class:`HtmxDetails <starlite.contrib.htmx.request.HtmxDetails>` class provides.


HTMX Response Classes
---------------------


HTMXTemplate Response Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most Common use-case while using HTMX is either full or partial html page. Starlite makes this easy by providing :class:`HTMXTemplate <starlite.contrib.htmx.response.HTMXTemplate>` response as follows:

.. code-block:: python

    from starlite.contrib.htmx.response import HTMXTemplate


    @get(path="/form")
    def get_form(
        request: HTMXRequest,
    ) -> Template:  # Return type is Template and not HTMXTemplate.
        ...
        return HTMXTemplate(
            name="partial.html",
            context=context,
            # Optional parameters
            push_url="/form",  # update browser history
            re_swap="outerHTML",  # change swapping method
            re_target="#new-target",  # change target element
            trigger_event="showMessage",  # trigger event name
            params={"alert": "Confirm your Choice."},  # parameter to pass to the event
            after="receive"  #  when to trigger event,
            # possible values 'receive', 'settle' and 'swap'
        )

.. note::
    - Return type is starlite's Template Type and not HTMXTemplate.
    - trigger_event, params and after parameters are linked to one another.
      If you are triggering an event then after value is required and must be one of 'receive', 'settle' or 'swap'.

HTMX provides two types of responses, one that don't change change DOM and one that changes DOM. Starlite supports these responses and they are as follows:

1 - Responses that don't make any changes to DOM.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    - :class:`HXStopPolling <starlite.contrib.htmx.response.HXStopPolling>` (Instruct HTMX client to stop polling for response.)

    .. code-block:: python

        @get("/")
        def handler() -> HXStopPolling:
            ...
            return HXStopPolling()

    - :class:`ClientRedirect  <starlite.contrib.htmx.response.ClientRedirect>` (Client side Redirect with page reload.)

    .. code-block:: python

        @get("/")
        def handler() -> ClientRedirect:
            ...
            return ClientRedirect(redirect_to="/contact-us")

    - :class:`ClientRefresh  <starlite.contrib.htmx.response.ClientRefresh>` (Full Refresh of page on client side.)

    .. code-block:: python

        @get("/")
        def handler() -> ClientRefresh:
            ...
            return ClientRefresh()

2 - Responses that may change DOM.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    - :class:`HXLocation <starlite.contrib.htmx.response.HXLocation>` (Instruct HTMX client to redirect to a new location without page reload and provides ability to change target, swapping method and send values and headers.)

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

    - :class:`PushUrl <starlite.contrib.htmx.response.PushUrl>` (May carry a response and instruct HTMX client to push url to browser history. If value to push_url is set to boolean False it will send "false" to htmx client to prevent it from updating browser history.)

    .. code-block:: python

        @get("/about")
        def handler() -> PushUrl:
            ...
            return PushUrl(content="Success!", push_url="/about")

    - :class:`ReplaceUrl <starlite.contrib.htmx.response.ReplaceUrl>` (May carry a response and instruct HTMX client to replace url in browser location bar. If value to replace_url is set to boolean False it will send "false" to htmx client to prevent it from updating browser location bar.)

    .. code-block:: python

        @get("/contact-us")
        def handler() -> ReplaceUrl:
            ...
            return ReplaceUrl(content="Success!", replace_url="/contact-us")

    - :class:`Reswap <starlite.contrib.htmx.response.Reswap>` (May carry a response and instruct HTMX client to different swapping method.)

    .. code-block:: python

        @get("/contact-us")
        def handler() -> Reswap:
            ...
            return Reswap(content="Success!", method="beforebegin")

    - :class:`Retarget <starlite.contrib.htmx.response.Retarget>` (May carry a response and instruct HTMX client to change the target element.)

    .. code-block:: python

        @get("/contact-us")
        def handler() -> Retarget:
            ...
            return Retarget(content="Success!", target="#new-target")

    - :class:`TriggerEvent <starlite.contrib.htmx.response.TriggerEvent>` (May carry a response and instruct HTMX client to trigger an event.)

    .. code-block:: python

        @get("/contact-us")
        def handler() -> TriggerEvent:
            ...
            return TriggerEvent(
                content="Success!",
                name="showMessage",
                params={"attr": "value"},
                after="receive",  # possible values 'receive', 'settle' and 'swap'
            )
