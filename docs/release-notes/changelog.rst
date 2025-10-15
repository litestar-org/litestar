:orphan:

3.x Changelog
=============

.. changelog:: 3.0.0
    :date: 2024-08-30


    .. change:: Remove all SQLAlchemy modules in favor of direct advanced-alchemy imports
        :type: feature
        :breaking:
        :pr: TBD

        Remove all SQLAlchemy functionality from Litestar. Both ``litestar.contrib.sqlalchemy``
        and ``litestar.plugins.sqlalchemy`` modules have been completely removed. Users must now
        import directly from ``advanced_alchemy.extensions.litestar``.

        Migration:
        - ``from litestar.contrib.sqlalchemy import X`` → ``from advanced_alchemy.extensions.litestar import X``
        - ``from litestar.plugins.sqlalchemy import Y`` → ``from advanced_alchemy.extensions.litestar import Y``

        This completes the separation of concerns, with advanced-alchemy being the sole provider
        of SQLAlchemy integration for Litestar.

    .. change:: Remove deprecated ``litestar.contrib.prometheus`` module
        :type: feature
        :breaking:
        :pr: 4328
        :issue: 4305

        Remove the deprecated ``litestar.contrib.prometheus`` module. Code still using imports
        from this module should switch to using ``litestar.plugins.prometheus``.


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

    .. change:: Remove deprecated ``litestar.contrib.htmx`` module
        :type: feature
        :breaking:
        :pr: 4316
        :issue: 4303

        Remove the deprecated ``litestar.contrib.htmx`` module. Code still using imports
        from this module should switch to using ``litestar_htmx``.

        Install it via ``litestar[htmx]`` extra.

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

    .. change:: Remove deprecated ``litestar.contrib.attrs`` module
        :type: feature
        :breaking:
        :pr: 4322
        :issue: 4302

        Remove the deprecated ``litestar.contrib.attrs`` module. Code still using imports
        from this module should switch to using ``litestar.plugins.attrs``.

    .. change:: Remove deprecated ``litestar.contrib.jwt`` module
        :type: feature
        :breaking:
        :pr: 4333
        :issue: 4304

        Remove the deprecated ``litestar.contrib.jwt`` module. Code still using imports
        from this module should switch to using ``litestar.security.jwt``.

    .. change:: Remove deprecated ``litestar.contrib.repository`` module
        :type: feature
        :breaking:
        :pr: 4337
        :issue: 4307

        Remove the deprecated ``litestar.contrib.repository`` module. Code still using imports
        from this module should switch to using ``litestar.repository``.

    .. change:: Remove deprecated ``litestar.contrib.pydantic`` module
        :type: feature
        :breaking:
        :pr: 4339
        :issue: 4306

        Remove the deprecated ``litestar.contrib.pydantic`` module. Code still using imports
        from this module should switch to using ``litestar.plugins.pydantic``.

    .. change:: Remove deprecated module ``litestar/contrib/minijnja``
        :type: feature
        :breaking:
        :pr: 4357
        :issue: 4357

        Remove the deprecated module ``litestar.contrib.minijnja``. This module was created with a typo in its name
        (`minijnja` instead of `minijinja`). Instead ``litestar.contrib.minijinja`` should be used.

    .. change:: Add ``round_trip`` parameter to ``PydanticPlugin``
        :type: feature
        :pr: 4350
        :issue: 4349

        New ``round_trip: bool`` parameter
        to :class:`~litestar.contrib.pydantic.PydanticPlugin` allows
        serializing types like ``pydanctic.Json`` correctly.

    .. change:: Remove deprecated ``litestar.contrib.minijinja.minijinja_from_state`` function
        :type: feature
        :breaking:
        :pr: 4355
        :issue: 4356

        Remove the deprecated ``litestar.contrib.minijinja.minijinja_from_state`` function.
        Instead use a callable that receives the minijinja ``State`` object as first argument.

    .. change:: Remove deprecated ``litestar.contrib.piccolo`` module
        :type: feature
        :breaking:
        :pr: 4363
        :issue: 4364

        Use ``litestar[piccolo]`` extra installation target
        and ``litestar_piccolo`` plugin instead:
        https://github.com/litestar-org/litestar-piccolo

    .. change:: Change ``Optional`` to ``NotRequired`` for pydantic fields with ``default_factory``
        :type: bugfix
        :pr: 4347
        :issue: 4294

        Now, in the OpenAPI schema, ``pydantic`` fields with ``default_factory`` are displayed as non-null and not required.
        Previously, this fields was nullable and not required.

    .. change:: Zero cost excluded middlewares
        :type: feature
        :breaking:

        Middlewares inheriting from :class:`~litestar.middleware.base.ASGIMiddleware`
        will now have zero runtime cost when they are excluded e.g. via the ``scope`` or
        ``exclude_opt_key`` options.

        Previously, the base middleware was always being invoked for every request,
        evaluating the exclusion criteria, and then calling the user defined middleware
        functions. If a middleware had defined ``scopes = (ScopeType.HTTP,)``, it would
        still be called for *every* request, regardless of the scope type. Only for
        requests with the type ``HTTP``, it would then call the user's function.

        .. note::
            This behaviour is still true for the legacy ``AbstractMiddleware``

        With *zero cost exclusion*, the exclusion is being evaluated statically. At app
        creation time, when route handlers are registered and their middleware stacks
        are being built, a middleware that is to be excluded will simply not be included
        in the stack.

        .. note::
            Even though this change is marked as breaking, no runtime behaviour
            difference is expected. Some test cases may break though if they relied on
            the fact that the middleware wrapper created by ``ASGIMiddleware`` was
            always being called

    .. change:: Support for ``typing.ReadOnly`` in typed dict schemas
        :type: feature
        :issue: 4423
        :pr: 4424

        Support unwrapping ``ReadOnly`` type in schemas like:

        .. code:: python

          from typing import ReadOnly, TypedDict

          class User(TypedDict):
              id: ReadOnly[int]

        ``typing_extensions.ReadOnly`` should be used for python versions <3.13.


    .. change:: Add ``should_bypass_for_scope`` to ``ASGIMiddleware`` to allow excluding middlewares dynamically
        :type: feature
        :pr: 4441

        Add a new attribute :attr:`~litestar.middleware.ASGIMiddleware.should_bypass_for_scope`;
        A callable which takes in a :class:`~litestar.types.Scope` and returns a boolean
        to indicate whether to bypass the middleware for the current request.
