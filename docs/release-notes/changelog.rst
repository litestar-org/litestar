:orphan:

3.x Changelog
=============

.. changelog:: 3.0.0
    :date: 2024-08-30

    .. change:: Make ``AsyncTestClient`` async-native
        :type: feature
        :pr: 4291
        :issue: 1920
        :breaking:

        Re-implement :class:`~litestar.testing.AsyncTestClient` to be async-native, i.e. use the currently running event
        loop to run the application, instead of running a separate event loop in a new thread. Additionally, a new
        :class:`~litestar.testing.AsyncWebSocketTestSession` has been introduced, providing an async testing utility
        for WebSockets.

        To ensure consisten behaviour across ``TestClient`` and ``AsyncTestClient``, all testing utilities have been
        rewritten to be async first, with their synchronous counterparts proxying calls to the async implementation,
        which they run internally within a dedicated thread + event loop.

        .. seealso::
            :ref:`usage/testing:Test Clients`
            :ref:`usage/testing:Deciding which test client to use`

    .. change:: Remove deprecated plugin properties from ``Litestar``
        :type: feature
        :pr: 4297
        :breaking:

        Remove deprecated ``<plugin_type>_plugins`` properties from :class:`Litestar`.

        ===================================  ===================================
        Removed                              Use instead
        ===================================  ===================================
        ``Litestar.openapi_schema_plugins``  ``Litestar.plugins.openapi_schema``
        ``Litestar.cli_plugins``             ``Litestar.plugins.cli``
        ``Litestar.serialization_plugins``   ``Litestar.serialization.cli``
        ===================================  ===================================

    .. change:: Remove deprecated ``allow_reserved`` and ``allow_empty_value`` property from ``ResponseHeader`` and ``OpenAPIHeader``
        :type: feature
        :pr: 4299
        :breaking:

        Remove the deprecated properties ``allow_reserved`` and ``allow_empty_value`` from
        :class:`~litestar.datastructures.ResponseHeader` and :class:`~litestar.openapi.spec.OpenAPIHeader`.

    .. change:: Remove deprecated ``traceback_line_limit`` parameter of ``LoggingConfig``
        :type: feature
        :breaking:
        :pr: 4300

        The ``traceback_line_limit`` parameter of :class:`~litestar.logging.config.LoggingConfig` has been removed. This
        parameter had no effect since version ``2.9.0``, so it can be removed safely from applications without any
        change in behaviour.

    .. change:: Remove deprecated ``litestar.middleware.cors`` module
        :type: feature
        :breaking:
        :pr: 4309

        Remove the deprecated ``litestar.middleware.cors`` module and ``litestar.middleware.cors.CORSMiddleware``. To
        configure the CORS middleware, use :class:`~litestar.config.cors.CORSConfig`.

    .. change:: Remove deprecated ``encoded_headers`` parameter from ASGI response classes and ``to_asgi_response`` methods
        :type: feature
        :pr: 4311
        :breaking:

        The deprecated ``encoded_headers`` parameter has been removed from the following clases:

        - :class:`~litestar.response.base.ASGIResponse`
        - :meth:`~litestar.response.Response.to_asgi_response`
        - :class:`~litestar.response.file.ASGIFileResponse`
        - :meth:`~litestar.response.File.to_asgi_response`
        - :class:`~litestar.response.redirect.ASGIRedirectResponse`
        - :meth:`~litestar.response.Redirect.to_asgi_response`
        - :class:`~litestar.response.streaming.ASGIStreamingResponse`
        - :meth:`~litestar.response.Stream.to_asgi_response`
        - :meth:`~litestar.response.Template.to_asgi_response`

        Existing code still using ``encoded_headers`` should be migrated to using the ``headers`` parameter instead.

    .. change:: Remove deprecated ``LitestarType``
        :type: feature
        :pr: 4312
        :breaking:

        Remove the deprecated ``litestar.types.internal_types.LitestarType`` type alias. In its stead,
        ``type[Litestar]`` can be used.

    .. change:: Remove deprecated ``TemplateContext``
        :type: feature
        :pr: 4313
        :breaking:

        Remove the deprecated ``litestar.template.base.TemplateContext`` type. Its usages should be replaced with
        :class:`collections.abc.Mapping`.

    .. change:: Remove deprecated ``ASGIResponse.encoded_headers`` property
        :type: feature
        :pr: 4314
        :breaking:

        Remove the deprecated ``ASGIResponse.encoded_headers`` property. Instead,
        :meth:`~litestar.response.base.ASGIResponse.encode_headers` should be used.

    .. change:: Remove deprecated ``pydantic_get_unwrapped_annotation_and_type_hints``
        :type: feature
        :pr: 4315
        :breaking:

        Remove the deprecated ``pydantic_get_unwrapped_annotation_and_type_hints`` function.
