:orphan:

3.x Changelog
=============

.. changelog:: 3.0.0
    :date: 2364-01-27

    .. change:: DTO: Faster startup and responses
        :type: misc

        Applications with many DTO handlers start faster and use less memory, and DTO handlers decode
        request bodies and encode responses faster. An object that lacks an attribute whose default
        is a factory or a mutable value is encoded more slowly than before. A DTO with
        ``__schema_name__`` whose request model has a constraint msgspec cannot enforce now fails at
        startup regardless of which handler is registered first.

    .. change:: DTO: A DTO declared on a route handler must apply
        :type: feature
        :breaking:
        :issue: 3485, 3553

        A ``dto`` or ``return_dto`` declared on a route handler, or in a ``WebsocketListener`` class
        body, that cannot handle the annotation now raises
        :exc:`~litestar.exceptions.DTONotApplicableError` at startup instead of being ignored. A DTO
        from a layer, the ``dto`` used for the return value, or a serialization plugin's DTO is
        skipped only when the annotation does not mention its model. A generic wrapper with more
        than one attribute holding the model is refused. Declare ``dto=None`` or
        ``return_dto=None`` on the handler to opt out. See
        :ref:`usage/dto/0-basic-use:When a DTO applies`.

    .. change:: DTO: Typed startup errors
        :type: feature
        :breaking:

        DTO errors raised at startup start with ``[paths=..., handler=...]``.
        ``DTONotApplicableError`` and ``DTOTransferTypeError`` subclass
        :exc:`~litestar.exceptions.InvalidAnnotationException`; ``MissingDTOError``, raised for
        ``DTOData`` without a DTO, subclasses ``DTOFactoryException`` and
        ``ImproperlyConfiguredException``. A return DTO over a type msgspec rejects raises
        ``DTOTransferTypeError`` when the OpenAPI schema is generated, instead of a ``TypeError``.
        Websocket listeners are named by their function or class instead of ``ListenerHandler``.

    .. change:: DTO: Unions of several types
        :type: feature
        :breaking:

        A DTO no longer handles an optional union of several types holding its model, such as
        ``User | int | None``, through its first member: it fails at startup. A return value
        annotated with a union of generic wrappers holding the model in one attribute, such as
        ``Page[User] | Cursor[User]``, is handled, and the OpenAPI schema of optional and nested
        generic wrappers shows the filtered model, which changes their component names.

    .. change:: DTO: Pass ``None`` through an optional annotation
        :type: bugfix
        :issue: 3428

        With an optional annotation, ``None`` now passes through a DTO instead of causing a
        ``500``: a handler can return ``None`` or ``Response(None)``, a ``null`` body is injected
        as ``None``, also for ``Optional[DTOData[Model]]``, and a websocket listener sends nothing.

    .. change:: DTO: Handle optional and nested collections of the model
        :type: bugfix

        An optional or nested collection such as ``Optional[list[Model]]``, ``list[Optional[Model]]``
        or ``dict[str, list[Model]]`` no longer causes a ``500``, and a generic wrapper whose attribute
        is optional, such as ``data: Optional[T] = None``, can hold ``None``.

    .. change:: DTO: Answer 400 for invalid form data
        :type: bugfix

        Invalid URL-encoded or multipart data decoded by a DTO now receives a ``400`` response, as
        invalid JSON data does, instead of a ``500``.

    .. change:: DTO: Apply a DTO to a handler annotation written as a type alias
        :type: bugfix

        When a DTO is declared or a serialization plugin provides one, a ``type`` statement or
        ``TypeAliasType`` alias in a handler annotation is handled like the type it stands for, in
        both directions and in the OpenAPI schema. With a declared DTO, an alias that cannot be
        resolved fails at startup.

    .. change:: DTO: Honour ``DTOField`` marks given as a string
        :type: bugfix
        :breaking:

        A mark given to :class:`~litestar.dto.field.DTOField` as a string, such as
        ``DTOField(mark="private")``, was ignored; it is now converted to
        :class:`~litestar.dto.field.Mark`, and an unknown mark raises :exc:`ValueError`. With
        ``forbid_unknown_fields=True``, clients sending such a field get a ``400``, and a
        ``"private"`` or ``"read-only"`` field now needs a default.

    .. change:: DTO: Stop requiring properties and computed fields in request data
        :type: bugfix

        ``DataclassDTO`` and ``MsgspecDTO`` required a model's properties in request data,
        and ``PydanticDTO`` its computed fields. Both are read-only and are no longer part of
        the inbound model.

    .. change:: DTO: Apply field filtering to nested models in fixed-length tuples
        :type: bugfix
        :breaking:
        :issue: 3342

        DTOs now filter and rename models nested in fixed-length tuples such as
        ``tuple[Model, int]``, and pass ``Model`` instances to handlers. Returning a tuple whose
        length differs from the annotation now fails with a ``500``.

    .. change:: DTO: Enforce ``Annotated`` constraints on every type a DTO rewrites
        :type: bugfix
        :breaking:
        :issue: 4181, 4195, 5025, 5031, 5051

        Constraints from ``msgspec.Meta``, ``annotated_types`` or parameter definitions are
        now enforced on every part of a field's type where msgspec can express them, also for
        partial DTOs; violating requests get a ``400``. An inbound DTO raises
        :exc:`~litestar.exceptions.DTOTransferTypeError` at startup, naming the field,
        for a ``Meta`` msgspec does not support where it is placed, such as
        ``Annotated[Optional[str], Meta(min_length=1)]``, and for an untagged union of models.
        See :ref:`usage/dto/1-abstract-dto:Constraints`.

    .. change:: DTO: ``MsgspecDTO.generate_field_definitions`` keeps the parsed ``kwarg_definition``
        :type: misc
        :breaking:

        :meth:`~litestar.dto.msgspec_dto.MsgspecDTO.generate_field_definitions` keeps the
        ``kwarg_definition`` parsed from the annotation instead of one built from ``msgspec.Meta``.

    .. change:: DTO: Field paths reach through an optional field without an index
        :type: bugfix
        :breaking:

        An ``exclude``, ``include`` or ``rename_fields`` entry such as ``"address.street"`` for a
        field ``address: Optional[Address]`` was ignored unless written with the member index, such
        as ``"address.0.street"``. It now applies to request data, responses and the OpenAPI schema.

    .. change:: DTO: Use a DTO backend without a request
        :type: feature

        The backend returned by ``AbstractDTO.create_for_field_definition`` decodes and
        encodes data with no application or request. ``handler_id`` and the connection
        are optional, raw data is read as JSON unless a ``media_type`` is passed, and
        ``type_decoders`` can be given when the backend is created.

    .. change:: DTO: Fix slow startup for self-referential and deeply nested models
        :type: bugfix
        :issue: 4235

        Fix slow startup and high memory use for DTOs of self-referential or deeply nested
        models. A custom ``attribute_accessor`` now reads a nested model once instead of once
        per field.

    .. change:: DTO: Fix the backend crashing for nested models
        :type: bugfix

        Fix a :exc:`SyntaxError` or :exc:`ValueError` at startup for models nested behind a
        single-field intermediate model or a custom ``attribute_accessor``, and for field
        names that are keywords or hold non-word characters. Fields whose names Python
        normalises, such as ``µ``, no longer read another field's value.

    .. change:: DTO: Name transfer models after their DTO
        :type: feature
        :breaking:
        :issue: 4699, 5102

        A DTO transfer model is named ``<DTO><RequestBody|ResponseBody>``, or after the
        DTO's ``__schema_name__``, and a nested one appends its field path joined by ``.``.
        Handlers using the same DTO share one model per application. A ``__schema_name__``
        gets the direction suffix when the DTO's request and response fields differ. An
        anonymous DTO such as ``DataclassDTO[Annotated[Model, DTOConfig(...)]]`` with a
        non-default config appends ``_`` and a fingerprint of that config. Names used by
        DTOs from different modules are qualified with their module in the OpenAPI schema.
        Every generated DTO component name changes, and subclasses overriding
        ``create_for_field_definition`` or passing a ``backend_cls`` must accept the new
        keyword-only ``transfer_models`` argument.

    .. change:: DTO: Store DTO backends on the route handler
        :type: misc
        :breaking:

        A route handler keeps the backends of its DTOs.
        ``AbstractDTO.create_for_field_definition`` returns the backend
        it builds instead of storing it on the DTO class, and
        ``AbstractDTO.create_openapi_schema`` takes the ``route_handler`` instead of a
        ``handler_id``.

    .. change:: DTO: Remove the non-codegen DTO backend
        :type: misc
        :breaking:

        DTOs always transfer data through the codegen backend, the default since
        ``2.8.0``. The ``DTOConfig.experimental_codegen_backend`` option and the private
        ``DTOCodegenBackend`` class are removed.

    .. change:: Add option to run the ASGI lifespan protocol for ``asgi`` handlers
        :type: feature

        Add a flag ``lifespan`` to :func:`~litestar.handlers.asgi`, defaulting to
        ``False``. When set to ``True``, the ASGI lifespan protocol will be ran for the
        handler, after the host app's ``on_startup`` hooks.

    .. change:: Add ``copy_state`` option to ASGI route handlers
        :type: feature

        Add a ``copy_state`` flag to :func:`~litestar.handlers.asgi`, defaulting to
        ``False``. It works similar to ``copy_scope``, and, if set, the mounted
        application will receive a shallow copy of ``scope["state"]``, so values it sets
        there are not seen by the outer application.

    .. change:: Don't allow layer parameters without an associated type
        :type: bugfix
        :breaking:
        :pr: 5247

        Fix a bug that would cause the constraints of a layer parameter, e.g.
        ``parameters={"limit": QueryParameter(gt=0)}``, to be silently ignored if no
        type information was associated with it. That is, it was declared without an
        explicit ``annotation=`` and did not correspond to any declared parameter in a
        handler or dependency provider.

        Since these cases are ambiguous (no type declared anywhere means there's no
        type to provide in the OpenAPI schema, and no type to validate against), they
        will now raise an :exc:`ImproperlyConfiguredException`.

    .. change:: Add ``documentation_only`` to parameter declarations
        :type: feature
        :pr: 5247

        Add :attr:`~litestar.params.ParameterKwarg.documentation_only`. If set, the
        constraints of a parameter are included in the OpenAPI schema, but not applied
        to the value of a request.

    .. change:: DTO: Identify the data a handler receives through its body marker
        :type: misc
        :breaking:
        :pr: 5242

        Refactor :meth:`~litestar.dto.base_dto.AbstractDTO.create_for_field_definition`
        and :meth:`~litestar.dto.base_dto.AbstractDTO.create_openapi_schema` to identify
        request vs. response body by the markers on the parameter itself, instead of its
        name (``data``).

    .. change:: Apply the DTO of a handler to a request body declared only in a dependency provider
        :type: bugfix
        :breaking:
        :pr: 5241

        Fix a bug that occurred when a request body was only declared in a dependency
        provider of a handler, with that handler setting a ``dto=``. The request body
        would not be decoded by the DTO, and would receive the raw DTO data, e.g. a
        ``dict``. The DTO will now always be taken into consideration, independent of
        the point the request body is declared.

    .. change:: Deprecate request parameters ``Headers``, ``QueryParams``, ``RequestCookies`` and ``Scope``
        :type: feature
        :pr: 5238

        Deprecate
        :class:`~litestar.datastructures.Headers`, :data:`~litestar.params.QueryParams`,
        :data:`~litestar.params.RequestCookies`, and :data:`~litestar.types.Scope` as
        request parameters.

        :class:`~litestar.connection.ASGIConnection`\ 's ``headers``, ``query_params``,
        ``cookies``, or ``scope`` attributes should be used instead.

    .. change:: Apply the constraints of a layer parameter to corresponding handler / DI parameters
        :type: bugfix
        :breaking:
        :pr: 5227

        Fix a bug that would cause the constraints of a layer parameter, e.g.
        ``parameters={"limit": QueryParameter(gt=0)}``, to not be applied for a
        corresponding handler or dependency parameter.

    .. change:: Apply the ``type_decoders`` of a handler to that handler only
        :type: bugfix
        :pr: 5227

        Fix a bug that would leak the type decoder of a request parameter to other
        handlers without that decoder.

    .. change:: Run all parts of sync generator dependencies in a worker threads
        :type: bugfix
        :breaking:
        :pr: 5227

        Run all code of a synchronous generator dependency in threads. Previously, code
        up until the first ``yield`` would run on the main thread.

        All of the generator's code runs in a shared :class:`contextvars.Context`.

    .. change:: Drop reserved keyword arguments in handlers and DI
        :type: feature
        :breaking:
        :pr: 5227

        Drop the special meaning of the "reserved keyword arguments" in handlers and DI
        providers.

        The parameter names can now freely be used and assigned, as their meaning is
        derived from their respective annotation:

        - ``data``
        - ``body``
        - ``request``
        - ``socket``
        - ``state``

        ``litestar.constants.RESERVED_KWARGS``, ``litestar.constants.SKIP_VALIDATION_NAMES``,
        ``FieldDefinition.is_non_marker_parameter_field`` and ``ParameterKwarg.is_marker``
        are removed.

    .. change:: Don't overwrite a handler parameter with a dependency of the same name
        :type: bugfix
        :breaking:
        :pr: 5227

        Fix a bug that would overwrite a request parameter in a handler with
        dependency of the same name. Request parameters now follow the same rule as
        dependencies: Last declared wins. Since a parameter in a handler is always
        declared last, it will always win against a dependency of the same name.

        The OpenAPI schema already documented this correctly.

    .. change:: OpenAPI: Exclude a layer parameter with ``include_in_schema=False`` from the schema
        :type: bugfix
        :pr: 5227

        Fix a bug that would cause a layer parameter declared with
        ``include_in_schema=False`` to still be included in the OpenAPI schema, if it
        was also consumed by a handler of a dependency of that handler.

    .. change:: OpenAPI: Include a layer parameter defined next to a handler parameter of the same name that doesn't bind it
        :type: bugfix
        :pr: 5227

        A handler parameter named like a layer parameter, with a marker that sets a field, is a
        parameter of its own, e.g. ``limit: Annotated[int, QueryParameter(ge=1)]`` under a layer
        parameter ``limit`` declared with ``name="page-limit"``. The OpenAPI schema documents
        both. Previously, it documented only the handler parameter.

    .. change:: OpenAPI: Document header parameters case insensitively across handlers and dependencies
        :type: bugfix
        :pr: 5227

        Fix a bug that would cause header parameters declared with different casings
        (e.g. ``X-Token`` and ``x-token``) to be documented as two distinct parameters,
        if one of them was declared in a dependency and one in a handler.

    .. change:: OpenAPI: Fix schema generation for request body declared only in a dependency provider and a DTO set
        :type: bugfix
        :pr: 5227

        Fix a bug that occurred when a request body was only declared in a dependency
        provider of a handler, with that handler setting a ``dto=``. The schema would be
        generated from the raw model, not the DTO transformed one. The schema now takes
        the DTO into consideration, independent of the point the request body is
        declared.

    .. change:: OpenAPI: Document the default of a handler parameter that's also a layer parameter
        :type: bugfix
        :pr: 5227

        Fix a bug that would document a handler / DI parameter declared with a default,
        *and* corresponding to a layer parameter *without a default*, as required and
        without a default.

        The parameter is now correctly documented as not required, and with its default.

    .. change:: Raise an exception at startup for variadic handler / DI parameters
        :type: bugfix
        :pr: 5227

        Raise an exception at startup if a handler or DI provider declares variadic
        parameters (``*args`` or ``**kwargs``).

        Previously, ``*args`` would fail every request with a ``500`` error, and
        ``**kwargs`` would implicitly declare a query parameter named ``kwargs``.

    .. change:: Raise an exception if a generator dependency yields more than once
        :type: bugfix
        :breaking:
        :pr: 5227

        Raise an exception if a generator dependency ``yield``\ s more than once.
        Previously, no exception was raised, and the code after the second ``yield``
        never ran.

    .. change:: Raise a startup exception if an unmarked handler parameter is named like a layer parameter
        :type: bugfix
        :breaking:
        :pr: 5227

        A handler parameter without a marker raises
        :class:`~litestar.exceptions.ImproperlyConfiguredException` at startup. Ensure
        this is also the case if it is named like a layer parameter.

    .. change:: Raise a startup exception if a request body is declared in a ``GET`` or websocket handler, or any of its dependencies
        :type: bugfix
        :breaking:
        :pr: 5227

        Raise a startup exception if a ``GET`` HTTP or a WebSocket handler, or any of
        their dependencies declare a request body.

        Previously, declaring a body for such handlers in a dependency would work, and
        the body would be passed as ``b""``, ignoring a possible default. Requests to
        a WebSocket handler with such a declaration would fail.

    .. change:: Fix channel subscriptions hanging after a send error or a full backlog
        :type: bugfix
        :pr: 5218

        Fix a bug where a channel subscription could hang forever, keeping the
        subscriber registered: after an error while sending an event (for example to a
        disconnected WebSocket client), after a ``dropleft`` backlog had overflowed,
        when unsubscribing or replaying history with a full ``backoff`` backlog, or when
        a WebSocket client stopped reading before disconnecting. The send error is now
        logged, a full backlog no longer blocks, and the WebSocket handler no longer
        waits to send queued events after the client disconnects.

    .. change:: Keep publishing channel messages after a backend error
        :type: bugfix
        :pr: 5213

        Fix a bug that stopped :class:`~litestar.channels.plugin.ChannelsPlugin` from publishing
        any further messages after the backend raised an error for one of them, for
        example a payload over the PostgreSQL ``NOTIFY`` size limit. Messages were
        queued but never sent, and shutting down the application hung. The error is
        now logged and publishing continues.

    .. change:: Do not cache parsed url-encoded form bodies
        :type: bugfix
        :pr: 5212

        Fix a bug that kept up to 1024 url-encoded request bodies and their parsed
        values in memory, so distinct large form submissions could grow memory until
        the process ran out. Url-encoded bodies are no longer cached.

    .. change:: Only accept known charsets for multipart form fields
        :type: bugfix
        :pr: 5211
        :breaking:

        Fix a bug that decoded multipart form fields with any Python codec named in the
        part's ``charset``. Codecs such as ``punycode`` decode in quadratic time and
        blocked the event loop, every unknown charset name was cached for the lifetime
        of the process, and an unknown charset or undecodable data caused a 500.

        Only charsets listed in the new ``multipart_form_allowed_charsets`` parameter of
        :class:`~litestar.app.Litestar` are accepted now; other charsets and invalid data
        return a 400. The default,
        ``litestar.constants.DEFAULT_MULTIPART_FORM_ALLOWED_CHARSETS``, accepts UTF-8,
        ASCII and ISO-8859-1, and any alias Python knows for them. Other charsets, such
        as ``windows-1252`` or ``shift_jis``, must now be added explicitly.

    .. change:: Fix the paths of the ``OPTIONS`` handler added under an app with a ``path``
        :type: bugfix
        :pr: 5208

        Fix a bug that gave the ``OPTIONS`` handler Litestar adds to a route the app's
        ``path`` twice in its ``paths``, e.g. ``/api/api/members`` on an app with
        ``path="/api"``. The handler was served under the correct path.

    .. change:: Call ``after_exception`` hooks once for an exception on a route with middleware
        :type: bugfix
        :pr: 5203

        Fix a bug that, on a route with middleware, an exception that no exception
        handler creates a response for, ``after_exception`` hooks and
        ``pdb_on_exception`` would be called multiple times (once by the exception
        handling layer of the middleware and once by the application's).

        They are called exactly once per exception instance now.

    .. change:: Remove support for trio
        :type: feature
        :breaking:
        :pr: 5201

        Trio is no longer supported. ``set_trio_capacity_limiter`` and
        ``get_trio_capacity_limiter`` are removed from :mod:`litestar.concurrency`, along with
        ``litestar.types.AnyIOBackend`` and the ``backend`` parameter of
        :class:`~litestar.testing.TestClient` and :func:`~litestar.testing.create_test_client`.
        :func:`~litestar.concurrency.sync_to_thread` raises ``RuntimeError`` when called from
        trio. ``sniffio`` is no longer a dependency.

    .. change:: Remove the ``litestar.pagination`` module
        :type: feature
        :breaking:
        :pr: 5199
        :issue: 4009

        The ``ClassicPagination``, ``OffsetPagination`` and ``CursorPagination`` containers,
        the six abstract paginator base classes and the internal OpenAPI schema plugin for
        the containers have been removed.

        ``OffsetPagination`` was re-exported from ``advanced_alchemy.service`` whenever that
        package was installed, so import it from there instead, adding Advanced Alchemy as a
        dependency if the application did not already have it. The other two containers and
        the paginator bases have no replacement; declare the container you need as a generic
        dataclass of your own. Every paginated handler's OpenAPI schema is now a ``$ref``
        component with ``required`` fields and without the plugin's per-field descriptions,
        so regenerate any client generated from the document.

    .. change:: DI: Correctly set Pydantic dependency fields as required without a default
        :type: bugfix
        :pr: 5195

        Fix a bug, causing a Pydantic model used as a dependency to fail at startup with
        ``Missing declaration for parameter`` for each of its fields without a marker,
        since ``PydanticDIPlugin`` marked them as dependencies only in the signature,
        not in the type hints used by the rest of the machinery.

    .. change:: DI: Correctly set ``msgspec.Struct`` dependency fields as required without a default
        :type: bugfix
        :pr: 5194

        Fix a bug that would implicitly give a field of an ``msgspec.Struct`` used as
        a dependency a default of ``msgspec.NODEFAULT`` and mark it as optional.
        Struct fields without a default are now correctly marked as required.

    .. change:: Parse every ``cookie`` header of a request
        :type: bugfix
        :breaking:
        :issue: 5177

        Only the first ``cookie`` header was parsed into
        :attr:`~litestar.connection.ASGIConnection.cookies`. Over HTTP/2 and HTTP/3 the
        header may repeat, and browsers send one per cookie, so every cookie but those in
        the first header went missing. All ``cookie`` headers are now parsed, joined with
        the ``"; "`` delimiter :rfc:`9113` and :rfc:`9114` prescribe.

        A cookie name sent more than once now keeps its first value, where it kept its last
        one before, following the :rfc:`6265` ordering that serialises the cookie of the
        longer path first. Scope a cookie holding a session or a CSRF token with the
        ``__Host-`` prefix so that a cookie of the same name, set under a longer path,
        cannot take precedence over it. ``cookies`` of
        :class:`~litestar.middleware.logging.LoggingMiddleware`'s response log likewise
        holds the first of several ``set-cookie`` headers of one name, not the last.

    .. change:: Restore a session split across several cookies over HTTP/2 and HTTP/3
        :type: bugfix
        :issue: 5177

        A session too large for one cookie is stored across several, named ``session-0``,
        ``session-1`` and so on. Over HTTP/2 and HTTP/3 only the chunks carried by the first
        ``cookie`` header were read, and
        :class:`~litestar.middleware.session.client_side.ClientSideSessionBackend` yields an
        empty session when it cannot decode the value in full, so such a session was
        silently dropped and the user logged out. Every chunk is now read.

    .. change:: Send repeated headers separately from the test client
        :type: bugfix
        :breaking:
        :issue: 5177

        The test client merged headers of the same name into one comma-joined header, which
        is invalid for ``cookie``, and left a request carrying a repeated header impossible
        to simulate. Repeated headers now reach the application as they were given, on
        requests and on :meth:`~litestar.testing.TestClient.websocket_connect`, which
        dropped all but the last of them.

        A test passing a header of the same name twice is affected: the application now
        receives the two values it was given, rather than one comma-joined value. Header
        values are also passed on as the bytes they were given in, where they were decoded
        and re-encoded as UTF-8 before.

    .. change:: Fix ``Optional`` / ``Any`` + ``required=False`` + without default parameters receiving ``Empty``
        :type: bugfix
        :breaking:
        :pr: 5185

        Fix a bug that would cause a request parameter typed ``Optional`` or ``Any``,
        *and* declared without a default *and* annotated as ``required=False`` to
        receive the ``Empty`` sentinel when that parameter was missing from the request.

        A parameter annotated ``required=False`` that is consumed by any handler or
        dependency, and does not have a default, now raises
        :class:`~litestar.exceptions.ImproperlyConfiguredException` at startup.

        This includes a marker for a parameter also declared as a layer parameter
        with ``required=False``. Layer parameters that are *not* consumed are not
        affected by this.

    .. change:: Fix ``ModuleNotFoundError`` when Pydantic or attrs are not installed
        :type: bugfix
        :issue: 5142

        Fix a bug that would raise :exc:`ModuleNotFoundError` when attrs or Pydantic
        were not installed.

    .. change:: ServerSideSessionBackend: Prevent storing empty sessions and session cookies for every request
        :type: bugfix
        :issue: 5182
        :pr: 5172

        Fix a bug where ``ServerSideSessionBackend`` would store an empty session under
        a new session ID and set a session cookie for every request, even when that
        request did not have a session cookie attached.

        The fixed backend will now only store a session if the client has a session
        cookie set. Empty sessions for a request with a session cookie will now also
        be deleted reliably.

    .. change:: Apply ``allow_symlinks_outside_directory=False`` to every part of a static file's path
        :type: bugfix
        :pr: 5181

        Fix a bug that would resolve symlinks only for the directory path, not the file
        path, when ``allow_symlinks_outside_directory=False``. The whole path is now
        always resolved.

    .. change:: Match mounted ASGI apps on path segments
        :type: bugfix
        :pr: 5178
        :issue: 5173
        :breaking:

        A mount matched any path merely *starting with* its path string, so a mount on
        ``/admin`` served ``/administrator``, handing the mounted app ``istrator/`` as its
        path. A mount now matches only its own path and sub-paths of it, ``/admin`` and
        ``/admin/...``, and ``/`` still mounts everything that no more specific mount
        claims.

        Of several mounts matching a path, the longest one now receives the request, so a
        mount nested under another, e.g. ``/admin/inner`` under ``/admin``, is reachable.
        This also fixes mounts sharing a prefix shadowing one another, and mount paths
        containing regex metacharacters, which raised ``500 - Internal Server Error`` or
        failed application startup.

        An application relying on a mount absorbing sibling paths that merely share its
        prefix now receives ``404 - Not Found`` for them. Mount the application one path
        segment higher, or declare the sibling path as a further path of the mount, e.g.
        ``@asgi(["/admin", "/administrator"], is_mount=True)``.

    .. change:: Default ``copy_scope`` to ``True`` for ASGI handlers
        :type: feature
        :breaking:
        :pr: 5164

        Every ``asgi`` handler, mounted or not, now receives a copy of the ASGI ``scope``,
        so the wrapped application can no longer add, replace or remove top-level scope
        keys seen by the outer application. The default was ``None``, which passed the
        original scope through, warned at registration and warned again when the wrapped
        application mutated the scope; both warnings are gone.

        The copy is shallow, so nested values such as ``scope["state"]`` are still shared
        with the outer scope.

        Set ``copy_scope=False`` where the wrapped application is meant to communicate with
        the outer application through the scope, for example by writing ``scope["user"]``
        for outer middleware to read, or by calling ``Request.set_session`` or
        ``Request.clear_session``. All of these now fail silently.

    .. change:: Remove support for declaring ``DTOField`` via Pydantic's ``Field.extra``
        :type: feature
        :breaking:
        :pr: 5163

        Declaring a ``DTOField`` through Pydantic's ``Field.extra``, that is
        ``Field(**dto_field("read-only"))``, is no longer supported. The mark was already
        ignored in 2.x and only emitted a deprecation warning. Remove the declaration and
        use ``Annotated[int, DTOField(mark="read-only")]`` instead; leaving it in place can
        make OpenAPI schema generation fail.

    .. change:: Declare ``socket`` in the original signature of a ``websocket_stream`` handler
        :type: bugfix
        :pr: 5161

        A ``websocket_stream`` handler whose function takes no ``socket`` parameter adds
        one to its ``parsed_fn_signature``, but only to its ``parameters``, so its
        ``original_signature`` lacked a parameter its ``parameters`` declared. It now
        declares ``socket`` in both.

    .. change:: Read constraint metadata on ``data`` as on any other parameter
        :type: bugfix
        :pr: 5157

        A ``data`` parameter annotated with metadata, e.g.
        ``data: Annotated[int, annotated_types.Gt(0)]``, was interpreted as a request
        body without a body marker, which got around the check of ``data`` being
        missing a marker

    .. change:: Require "reserved kwargs" to be declared with their type
        :type: feature
        :breaking:
        :pr: 5154

        Declaring the "reserved kwargs" ``body``, ``cookies``, ``data``,
        ``headers``, ``query``, ``request``, ``scope`` and ``socket`` without the type
        listed below, or with a different one, raises
        :class:`~litestar.exceptions.ImproperlyConfiguredException` at startup.

        For this, add the types :data:`~litestar.params.RawBody`,
        :data:`~litestar.params.QueryParams` and :data:`~litestar.params.RequestCookies`,
        and the body marker :data:`~litestar.params.RequestBody`, which declares a body
        of the default media type, ``application/json``.

        .. list-table::
            :header-rows: 1
            :widths: 20 80

            * - Parameter
              - Type
            * - ``body``
              - :data:`~litestar.params.RawBody`
            * - ``cookies``
              - :data:`~litestar.params.RequestCookies`
            * - ``data``
              - A body marker, e.g. :data:`~litestar.params.JSONBody` or
                :data:`~litestar.params.RequestBody`
            * - ``headers``
              - :class:`~litestar.datastructures.Headers`
            * - ``query``
              - :data:`~litestar.params.QueryParams`
            * - ``request``
              - The request class configured for the handler, or one of its base classes,
                e.g. :class:`~litestar.connection.Request`
            * - ``scope``
              - :data:`~litestar.types.Scope`
            * - ``socket``
              - The websocket class configured for the handler, or one of its base
                classes, e.g. :class:`~litestar.connection.WebSocket`

        ``headers`` receives the request's :class:`~litestar.datastructures.Headers`.
        Before, ``headers: dict[str, str]`` received a :class:`dict` and
        ``headers: Headers`` failed validation with a ``400 - Bad Request``.

        In route handlers, ``cookies``, ``headers``, ``query`` and ``scope`` can also be
        accessed through the request, e.g. ``request.headers``.

        .. seealso:: :ref:`handler-function-kwargs`

    .. change:: Remove support for implicitly declared request parameters
        :type: feature
        :breaking:
        :pr:

        Remove the deprecated implicit request parameter declaration. All request
        parameters must now be explicitly marked (e.g. with
        :data:`~litestar.params.FromQuery`).

        .. list-table::
            :header-rows: 1
            :widths: 45 55

            * - Deprecated
              - Use instead
            * - ``def h(name: str)`` *(implicit query parameter)*
              - ``def h(name: FromQuery[str])``
            * - ``def h(user_id: int)`` *(implicit path parameter)*
              - ``def h(user_id: FromPath[int])``
            * - ``Annotated[str, Parameter(query="alias")]``
              - ``Annotated[str, QueryParameter(name="alias")]``
            * - ``Annotated[str, Parameter(header="X-API-KEY")]``
              - ``Annotated[str, HeaderParameter(name="X-API-KEY")]``
            * - ``Annotated[str, Parameter(cookie="session")]``
              - ``Annotated[str, CookieParameter(name="session")]``
            * - ``name: str = Parameter(...)`` *(default-value style)*
              - ``name: Annotated[str, QueryParameter(...)]``

        .. seealso::
            :doc:`/usage/routing/parameters`

    .. change:: Only read parameters marked as path parameters from the path
        :type: bugfix
        :pr: 5128
        :breaking:

        A parameter whose name matched a path segment was read from the path even when it
        was marked with ``FromQuery``, ``FromHeader``, ``FromCookie`` or the corresponding
        ``Parameter`` kwarg, and was documented as a path parameter. Such a parameter is
        now read from, and documented at, the location it is marked with.

        A parameter named like a path segment that declares no location, the deprecated
        inferred path parameter style, now raises ``ImproperlyConfiguredException`` when
        the application is created. Declare it with ``FromPath``.

    .. change:: Migrate ``SessionMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 5060
        :issue: 4009
        :breaking:

        :class:`~litestar.middleware.session.base.SessionMiddleware` has been moved from the
        legacy ``AbstractMiddleware`` base to :class:`~litestar.middleware.ASGIMiddleware`,
        as part of migrating all built-in middleware off the legacy bases.

        The middleware still takes a session backend, which keeps receiving its
        configuration unchanged, but no longer wraps an ``app``. The ``middleware``
        property of :class:`~litestar.middleware.session.server_side.ServerSideSessionConfig`
        and :class:`~litestar.middleware.session.client_side.CookieBackendConfig` now returns
        a ``SessionMiddleware`` instance instead of a ``DefineMiddleware`` wrapping it, so
        applications using ``middleware=[session_config.middleware]`` are unaffected. Code
        that constructed the middleware directly, or introspected the ``DefineMiddleware``,
        must be updated:

        .. code-block:: python

            # before
            middleware = SessionMiddleware(app=next_app, backend=backend)
            backend = session_config.middleware.kwargs["backend"]

            # after
            middleware = SessionMiddleware(backend=backend)
            asgi_app = middleware(next_app)
            backend = session_config.middleware.backend

        The new ``exclude_path_pattern`` option of the session configurations matches
        against the handler's path (e.g. ``/user/{user_id:int}``); handlers excluded this
        way, or via ``exclude_opt_key``, bypass the middleware entirely at startup rather
        than per request.

        Since ``ASGIMiddleware.__call__`` returns a closure rather than the middleware
        instance, a middleware stack can no longer be introspected by walking the ``.app``
        attribute of each layer.

        .. seealso::
            :ref:`asgi-middleware-migration`

    .. change:: Migrate ``PrometheusMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 5006
        :issue: 4009
        :breaking:

        ``PrometheusMiddleware`` has been moved from the legacy ``AbstractMiddleware``
        base to :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all
        built-in middleware off the legacy bases.

        Since the middleware is now directly constructible, the
        :class:`~litestar.plugins.prometheus.PrometheusConfig` configuration object is
        obsolete and its ``middleware`` property is deprecated; it will be removed in
        ``4.0``. Pass a configured ``PrometheusMiddleware`` instance to the middleware
        list instead:

        .. code-block:: python

            # before
            config = PrometheusConfig(app_name="my-app", group_path=True)
            app = Litestar(..., middleware=[config.middleware])

            # after
            app = Litestar(
                ...,
                middleware=[PrometheusMiddleware(app_name="my-app", group_path=True)],
            )

        Subclasses of ``PrometheusMiddleware`` must rename ``__call__`` to ``handle``,
        which receives the next ASGI app as an additional ``next_app`` argument in place
        of ``self.app``, and read settings from the corresponding instance attributes
        instead of the removed private ``self._config``.

        ``exclude`` patterns are still matched against the request path. The new
        ``exclude_path_pattern`` argument matches against the handler's path (e.g.
        ``/user/{user_id:int}``) instead; handlers excluded this way, or via
        ``exclude_opt_key``, bypass the middleware entirely at startup rather than per
        request.

        Mounted ASGI apps stay wrapped regardless of the configured ``scopes``, with
        their connections filtered by scope type at runtime, so restricting the
        middleware to e.g. ``{"websocket"}`` also holds for connections through mounts.

    .. change:: Migrate ``RateLimitMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 5005
        :issue: 4009
        :breaking:

        ``RateLimitMiddleware`` has been moved from the legacy ``AbstractMiddleware``
        base to :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all
        built-in middleware off the legacy bases.

        Since the middleware is now directly constructible, the
        :class:`~litestar.middleware.rate_limit.RateLimitConfig` configuration object is
        obsolete and its ``middleware`` property is deprecated; it will be removed in
        ``4.0``. Pass a configured ``RateLimitMiddleware`` instance to the middleware
        list instead:

        .. code-block:: python

            # before
            config = RateLimitConfig(rate_limit=("minute", 10), exclude=["/schema"])
            app = Litestar(..., middleware=[config.middleware])

            # after
            app = Litestar(
                ...,
                middleware=[RateLimitMiddleware(rate_limit=("minute", 10), exclude=["/schema"])],
            )

        ``exclude`` patterns are still matched against the request path. The new
        ``exclude_path_pattern`` argument matches against the handler's path (e.g.
        ``/user/{user_id:int}``) instead; handlers excluded this way, or via
        ``exclude_opt_key``, bypass the middleware entirely at startup rather than per
        request.

    .. change:: Add support for ``leeway`` parameter in JWT security backends
        :type: feature
        :pr: 5037
        :issue: 4584
        :breaking:

        Add support for ``leeway`` parameter in JWT security backends, which allows set
        a number of potential seconds as a clock error for expired tokens.

        ``Token.decode`` and ``Token.decode_payload`` now take a ``leeway`` argument.
        Custom token classes overriding either method must accept it and forward to
        ``super()``, otherwise decoding raises ``TypeError``.

    .. change:: Fix ``TypeError`` when generating a schema for a union of enums
        :type: bugfix
        :pr: 4997

        Annotating a handler with a union whose members are all enums (e.g.
        ``Color | Size``) crashed schema generation with ``TypeError: issubclass()
        arg 1 must be a class``, as the union was dispatched to the enum schema
        handler. Such unions are now documented as a ``oneOf`` with a component
        schema per enum.

    .. change:: Return HTTP 413 when the multipart form part limit is exceeded
        :type: feature
        :pr: 4990
        :issue: 4439
        :breaking:

        Exceeding the configured multipart form part limit now returns
        ``413 Request Entity Too Large`` instead of ``400 Bad Request``.

    .. change:: Remove the RapiDoc OpenAPI UI plugin
        :type: feature
        :pr: 4977
        :breaking:

        The ``RapidocRenderPlugin`` has been removed due to lack of upstream maintenance.

        Applications using ``RapidocRenderPlugin`` should migrate to another bundled UI
        plugin, such as ``ScalarRenderPlugin`` (the default), ``SwaggerRenderPlugin``,
        ``RedocRenderPlugin`` or ``StoplightRenderPlugin``.

    .. change:: Migrate ``AllowedHostsMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 5001
        :issue: 4009
        :breaking:

        ``AllowedHostsMiddleware`` has been moved from the legacy ``AbstractMiddleware``
        base to :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all
        built-in middleware off the legacy bases.

        Applications that configure allowed hosts through
        :class:`~litestar.config.allowed_hosts.AllowedHostsConfig` or the
        ``allowed_hosts`` argument are unaffected, since Litestar constructs the
        middleware itself. The constructor takes keyword arguments now instead of an
        ``app`` and an ``AllowedHostsConfig``:

        .. code-block:: python

            # before
            middleware = AllowedHostsMiddleware(app=next_app, config=config)

            # after
            middleware = AllowedHostsMiddleware(
                allowed_hosts=config.allowed_hosts,
                exclude=config.exclude,
                exclude_opt_key=config.exclude_opt_key,
                scopes=config.scopes,
                www_redirect=config.www_redirect,
            )
            asgi_app = middleware(next_app)

        :attr:`~litestar.config.allowed_hosts.AllowedHostsConfig.exclude` patterns are
        still matched against the request path. The new
        :attr:`~litestar.config.allowed_hosts.AllowedHostsConfig.exclude_path_pattern`
        matches against the handler's path (e.g. ``/user/{user_id:int}``) instead;
        handlers excluded this way, or via ``exclude_opt_key``, bypass the middleware
        entirely at startup rather than per request.

    .. change:: Migrate ``CompressionMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 4999
        :issue: 4009
        :breaking:

        ``CompressionMiddleware`` has been moved from the legacy ``AbstractMiddleware``
        base to :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all
        built-in middleware off the legacy bases.

        Applications that configure compression through
        :class:`~litestar.config.compression.CompressionConfig` are unaffected, since
        Litestar constructs the middleware itself. The middleware still takes the
        ``CompressionConfig`` - which the ``CompressionFacade`` protocol continues to
        receive unchanged - but no longer wraps an ``app``:

        .. code-block:: python

            # before
            middleware = CompressionMiddleware(app=next_app, config=config)

            # after
            middleware = CompressionMiddleware(config=config)
            asgi_app = middleware(next_app)

        Subclasses set via
        :attr:`~litestar.config.compression.CompressionConfig.middleware_class` must
        rename ``__call__`` to ``handle``, which receives the next ASGI app as an
        additional ``next_app`` argument in place of ``self.app``.

        :attr:`~litestar.config.compression.CompressionConfig.exclude` patterns are still
        matched against the request path. The new
        :attr:`~litestar.config.compression.CompressionConfig.exclude_path_pattern`
        matches against the handler's path (e.g. ``/user/{user_id:int}``) instead;
        handlers excluded this way, or via ``exclude_opt_key``, bypass the middleware
        entirely at startup rather than per request.

    .. change:: Migrate ``CSRFMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 4998
        :issue: 4009
        :breaking:

        ``CSRFMiddleware`` has been moved from the legacy ``MiddlewareProtocol`` base to
        :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all built-in
        middleware off the legacy bases. It now lives in ``litestar.middleware._internal``.
        This removes the ``litestar.middleware.csrf`` module, including the
        ``generate_csrf_token`` and ``generate_csrf_hash`` helpers, from the public API.

        Applications that configure CSRF protection through
        :class:`~litestar.config.csrf.CSRFConfig` are unaffected, since Litestar
        constructs the middleware itself, via a ``from_config`` classmethod on the
        middleware.

        :attr:`~litestar.config.csrf.CSRFConfig.exclude` patterns are still matched
        against the request path. The new
        :attr:`~litestar.config.csrf.CSRFConfig.exclude_path_pattern` matches against the
        handler's path (e.g. ``/user/{user_id:int}``) instead; handlers excluded this way,
        or via ``exclude_from_csrf``, bypass the middleware entirely at startup rather
        than per request.

    .. change:: Migrate ``ResponseCacheMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 4953
        :issue: 4009
        :breaking:

        ``ResponseCacheMiddleware`` has been moved from the legacy ``AbstractMiddleware``
        base to :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all
        built-in middleware off the legacy bases. It now lives in
        ``litestar.middleware._internal``, removing it from the public API.

        .. note::
            The move into ``litestar.middleware._internal`` does not affect usage:
            the middleware was only ever applied internally by Litestar to begin with.

        Applications that configure response caching through
        :class:`~litestar.config.response_cache.ResponseCacheConfig` and the handler-level
        ``cache`` argument are unaffected -- Litestar constructs the middleware itself.

        Code composing the middleware directly into an ASGI stack must drop the ``app``
        argument, pass the settings as keyword arguments rather than a
        ``ResponseCacheConfig``, and apply the instance to the next ASGI app:

        .. code-block:: python

            # before
            middleware = ResponseCacheMiddleware(app=next_app, config=response_cache_config)

            # after
            middleware = ResponseCacheMiddleware(
                default_expiration=response_cache_config.default_expiration,
                key_builder=response_cache_config.key_builder,
                store=response_cache_config.store,
                cache_response_filter=response_cache_config.cache_response_filter,
            )
            asgi_app = middleware(next_app)

        Since ``ASGIMiddleware.__call__`` returns a closure rather than the middleware
        instance, a middleware stack can no longer be introspected by walking the ``.app``
        attribute of each layer.

        .. seealso::
            :ref:`asgi-middleware-migration`

    .. change:: Migrate ``CORSMiddleware`` to ``ASGIMiddleware``
        :type: feature
        :pr: 4952
        :issue: 4009
        :breaking:

        ``CORSMiddleware`` has been moved from the legacy ``AbstractMiddleware`` base to
        :class:`~litestar.middleware.ASGIMiddleware`, as part of migrating all built-in
        middleware off the legacy bases.

        Applications that configure CORS through
        :class:`~litestar.config.cors.CORSConfig` are unaffected -- Litestar constructs
        the middleware itself.

        Code instantiating the middleware directly must drop the ``app`` argument, pass
        the settings as keyword arguments rather than a ``CORSConfig``, and apply the
        instance to the next ASGI app:

        .. code-block:: python

            # before
            middleware = CORSMiddleware(app=next_app, config=cors_config)

            # after
            middleware = CORSMiddleware(allow_origins=cors_config.allow_origins, ...)
            asgi_app = middleware(next_app)

        The settings are copied on construction, so mutating ``CORSConfig`` after the
        application has been created no longer affects the middleware.

        Since ``ASGIMiddleware.__call__`` returns a closure rather than the middleware
        instance, a middleware stack can no longer be introspected by walking the ``.app``
        attribute of each layer.

        .. seealso::
            :ref:`asgi-middleware-migration`

    .. change:: Stop caching responses of handlers that do not enable caching
        :type: bugfix
        :pr: 4953

        ``ResponseCacheMiddleware`` is applied per route, so a handler that never set
        ``cache`` still had its responses written to the store when it shared a path with
        a handler that did -- for example a ``POST`` handler on a path whose ``GET``
        handler sets ``cache=True``. Those entries were written on every request, without
        an expiry, and were never read back, since responses are only served from the
        cache for handlers that enable it.

        The middleware now passes such requests through untouched.
    .. change:: Harden the PsycoPg channels listener
        :type: bugfix

        Serialize subscription changes and consume notifications in a background task so
        dynamic ``LISTEN`` and ``UNLISTEN`` operations no longer contend with the listener.
        Psycopg 3.2.4 or newer is now required for development and documentation builds.

    .. change:: Base the test clients on ``httpx2``
        :type: feature
        :pr: 4974
        :breaking:

        The ``litestar[testing]`` extra now installs `httpx2 <https://pydantic.dev/docs/httpx2/>`_,
        the fork of ``httpx`` maintained by Pydantic, instead of ``httpx``.

        ``httpx2`` keeps the public API of ``httpx`` 0.28.1, but it is a distinct module,
        so every ``httpx`` reference in a test suite has to be renamed, including
        annotations such as ``response: httpx.Response``. Its exceptions no longer
        inherit from the ``httpx`` ones, so an ``except httpx.HTTPError`` around a test
        client call stops matching, silently where ``httpx`` remains installed for other
        reasons. Beyond the rename:

        - ``TestClient`` and ``AsyncTestClient`` now subclass ``httpx2.Client`` and
          ``httpx2.AsyncClient``, and ``subprocess_sync_client`` /
          ``subprocess_async_client`` return ``httpx2`` clients.
        - The logger is named ``httpx2``, which affects logging configuration and
          ``caplog`` assertions that reference the ``httpx`` logger.
        - The clients inherit ``httpx2``'s ``sse()``, so ``httpx-sse`` is no longer
          needed. The inherited ``websocket()`` does not work against the test
          transport; use :meth:`~litestar.testing.TestClient.websocket_connect` instead.
        - The subprocess clients send ``User-Agent: python-httpx2/<version>``;
          ``TestClient`` and ``AsyncTestClient`` keep sending ``testclient``.
        - The extra pulls ``anyio>=4.10`` and ``idna>=3.18``, neither of which can be
          satisfied alongside a lower pin, and verifies TLS against the operating system
          trust store via ``truststore`` rather than ``certifi``.

        ``httpx2.alias_httpx()``, which must run before anything imports ``httpx`` or
        ``httpcore``, makes ``import httpx`` resolve to ``httpx2`` process-wide for
        suites that cannot be renamed yet. Litestar never calls it.

        .. seealso::
            :doc:`/usage/testing`

    .. change:: Move ``httpx`` to the ``testing`` extra
        :type: feature
        :pr: 4950
        :breaking:

        ``httpx``, used by the test clients, has been moved from the default dependencies
        to the ``litestar[testing]`` extra, which is included in ``litestar[full]``. The
        extra went on to replace ``httpx`` with ``httpx2`` altogether, so 3.0 ships no
        dependency on ``httpx``.

        Importing anything from ``litestar.testing`` without the extra installed now
        raises a ``MissingDependencyException`` naming the extra to install.

        .. seealso::
            :doc:`/usage/testing`

    .. change:: Require ``rich-click>=1.9``
        :type: feature
        :pr: 4951
        :breaking:

        The ``litestar[cli]`` extra now requires ``rich-click>=1.9``. ``rich-click`` was
        previously capped at ``<1.9``, which silently disabled the CLI's ``star-box``
        theme: the underlying ``theme`` option only exists from 1.9 onwards, and
        assigning an unknown setting is ignored rather than raising.

        The CLI configuration has been migrated off the options 1.9 deprecates
        (``use_markdown`` / ``use_rich_markup`` in favour of ``text_markup``, and
        ``show_metavars_column`` / ``append_metavars_help`` in favour of
        ``options_table_column_types`` / ``options_table_help_sections``).

        The layout of the help output is preserved: option tables keep the long form in
        the first column, the ``*`` marker on required parameters, and the metavar
        appended directly after the help text. Colours do change, as the ``star-box``
        theme now takes effect for the first time.

        This only affects applications that additionally pin ``rich-click<1.9``
        themselves.

        .. seealso::
            :doc:`/usage/cli`

    .. change:: Move ``click``, ``rich`` and ``rich-click`` to the ``cli`` extra
        :type: feature
        :pr: 4949
        :breaking:

        ``click``, ``rich`` and ``rich-click``, which power the CLI, have been moved from
        the default dependencies to the ``litestar[cli]`` extra. They remain included in
        ``litestar[standard]`` and ``litestar[full]``.

        Installing ``litestar`` on its own therefore no longer provides the ``litestar``
        command. Invoking it without the extra now raises a
        ``MissingDependencyException`` naming the extra to install.

        .. seealso::
            :doc:`/usage/cli`

    .. change:: Remove deprecated ``litestar.contrib`` namespace
        :type: feature
        :issue: 4720
        :breaking:

        Remove the deprecated ``litestar.contrib`` namespace. Integrations previously
        available from this namespace have moved to their replacement modules.

    .. change:: Remove deprecated declaration of metadata through default values
        :type: feature
        :pr: 4819
        :breaking:

        Remove declaring parameter and body metadata through default values and setting
        defaults inside markers.

        - The ``default`` keyword has been removed from ``Parameter`` and ``Body``, along
          with the underlying ``KwargDefinition.default`` field. Passing it now raises a
          ``TypeError``.
        - Using a ``QueryParameter`` / ``HeaderParameter`` / ``PathParameter`` /
          ``CookieParameter`` or ``Body`` marker as a parameter *default value* (for
          example ``data: Foo = Body(...)`` or ``param: int = QueryParameter(...)``)
          now raises an exception

        **Migration**

        - If metadata is declared on the marker, move the marker into ``Annotated``:

          - ``data: Foo = Body(min_items=2)`` becomes ``data: Annotated[Foo, Body(min_items=2)]``
          - ``param: int = QueryParameter(gt=1)`` becomes ``param: Annotated[int, QueryParameter(gt=1)]``

          For the unconstrained case the dedicated markers can be used as a shorthand,
          e.g. ``JSONBody[Foo]``, ``MsgPackBody[Foo]``, ``MultipartBody[Foo]`` or
          ``URLEncodedBody[Foo]`` for bodies, and ``FromQuery[int]``, ``FromHeader[int]``,
          ``FromCookie[int]`` or ``FromPath[int]`` for parameters.

        - Hoist defaults set inside ``Annotated`` into the parameter default:
          ``param: Annotated[int, QueryParameter(default=5)]`` becomes
          ``param: Annotated[int, QueryParameter(...)] = 5``.

        .. seealso::
            :doc:`/usage/routing/parameters`

    .. change:: Remove deprecated ``params.Dependency`` and ``params.DependencyKwarg``
        :type: feature
        :pr: 4818
        :breaking:

        Remove ``params.Dependency`` and ``params.DependencyKwarg`` that were deprecated
        in ``2.23.0``.

        **Migration**

        - Replace ``foo: int = Dependency()`` with ``foo: NamedDependency[int]``
        - Replace ``foo: Annotated[int, Dependency(default=1)]`` by hoisting the
          default into the parameter default: ``foo: NamedDependency[int] = 1``
        - Replace ``foo: Annotated[int, Dependency(skip_validation=True)`` with
          ``foo: NamedDependency[SkipValidation[int]]``

    .. change:: Fix OpenAPI schema incorrectly marking nullable required fields as not required
        :type: bugfix
        :pr: 4687
        :issue: 4673

        Fields typed as ``T | None`` (nullable) without a default value are now correctly
        included in the OpenAPI schema's ``required`` array. Previously, Litestar conflated
        nullability (the type can be ``None``) with optionality (having a default value),
        causing the generated schema to diverge from the OpenAPI 3.1.0 specification.

        This affected all model types: dataclasses, msgspec Structs, attrs classes, and
        Pydantic models. For example, a field ``name: int | None`` with no default was
        previously excluded from ``required``; it is now correctly included.

        Runtime request validation behavior is unchanged — nullable parameters without
        defaults were already enforced as required at the validation layer.

    .. change:: Drop support for Pydantic 1
        :type: feature
        :breaking:

        Drop support for Pydantic 1.

        Pydantic 1 is no longer supported or tested against. No changes required for
        applications already using Pydantic 2. Applications using Pydantic 1 or a mix
        between 1 and 2 should upgrade to Pydantic 2.

    .. change:: Add ``ping_interval`` to ``ServerSentEvent`` for keepalive pings
        :type: feature
        :pr: 4623
        :issue: 4082

        Added optional ``ping_interval`` parameter to :class:`ServerSentEvent <litestar.response.ServerSentEvent>` that
        sends SSE comment keepalive pings at the specified interval to prevent connection timeouts from reverse proxies
        or clients.

    .. change:: Remove logging config and related constructs
        :type: feature
        :breaking:
        :pr: 4615
        :issue: 2858, 3913, 3455

        Remove Litestar's logging configuration, and related modules. In particular,
        the following have been removed:

        - ``Litestar.logging_config`` parameter
        - ``Litestar.logger`` attribute
        - ``Litestar.get_logger`` method
        - ``AppConfig.logging_config`` attribute
        - ``ASGIConnection.logger`` property
        - ``litestar.logging`` module
        - ``litestar.plugins.structlog`` module
        - ``litestar.middleware.lgging.LoggingMiddlewareConfig`` class

        Aside from debugging, there is only one place where Litestar logs, which is
        :class:`~litestar.middleware.logging.LoggingMiddleware`, which has been changed
        to accept a logger directly.
        ``litestar.middleware.lgging.LoggingMiddlewareConfig`` has also been removed,
        with ``LoggingMiddleware`` now accepting all configuration arguments directly.

        Users that have previously relied on Litestar to configure logging, can simply
        use the standard logging configuration provided by their logging library of
        choice.

        .. seealso::
            :doc:`/usage/logging`


    .. change:: Remove default exception handler for all unhandled exceptions
        :type: feature
        :breaking:
        :pr: 4610

        Remove the default exception handler for all unhandled exceptions. Unhandled
        exceptions will now be re-raised, for the server to handle.
        "Unhandled exceptions" in this context means any exception for which no custom
        exception handler exist, and that does not derive from :exc:`LitestarException`
        or :exc:`HTTPException`.

        .. important::

            Your application's runtime behaviour won't change in terms of *if*
            exceptions get handled. The main difference will be that, for an unhandled
            exception, it will be the ASGI server that creates a
            ``500 - Internal Server Error`` response, instead of Litestar

    .. change:: Fix ``raise_server_exceptions`` flag in test clients
        :type: bugfix
        :pr: 4610

        Fix the ``raise_server_exceptions``. This flag has been non-functional (i.e. did
        not change the behaviour at all) since version 1. This is now fixed, and
        unhandled exceptions will be re-raised by the test client

    .. change:: Fix swallowing of unhandled exceptions in WebSocket client
        :type: bugfix
        :pr: 4610

        Fix a bug that could lead to unhandled exceptions raised within websocket
        handlers, and not derived from :exc:`LitestarException` or :exc:`HTTPException`
        to be silently swallowed. This would lead to a closing of the WebSocket
        connection without any indication of an exception

    .. change:: Remove all SQLAlchemy modules in favor of direct advanced-alchemy imports
        :type: feature
        :breaking:
        :pr: 4340

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

        The ``traceback_line_limit`` parameter of ``litestar.logging.config.LoggingConfig`` has been removed. This
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
        to ``PydanticPlugin`` allows
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

    .. change:: Move ``litestar.contrib.opentelemetry`` to ``litestar.plugins.opentelemetry`` and add upstream parity
        :type: feature
        :breaking:
        :pr: 4691
        :issue: 4466, 4468

        Move the OpenTelemetry integration from ``litestar.contrib.opentelemetry`` to
        ``litestar.plugins.opentelemetry``. Code still using imports from the old
        module should switch to the new path.

        :class:`~litestar.plugins.opentelemetry.OpenTelemetryConfig` has been brought
        in line with the upstream
        ``opentelemetry.instrumentation.asgi.OpenTelemetryMiddleware`` configuration,
        adding ``client_request_hook_handler``, ``client_response_hook_handler``,
        ``tracer``, ``exclude``, ``exclude_opt_key``, ``exclude_urls_env_key``,
        ``exclude_spans``, ``http_capture_headers_server_request``,
        ``http_capture_headers_server_response``, and
        ``http_capture_headers_sanitize_fields``.

        Also fixes a ``KeyError: 'route_handler'`` raised on every request when
        ``exclude_opt_key`` was set, and corrects the ``OpenTelemetryHookHandler``
        signature to accept the span, ASGI scope, and ASGI message as documented by
        upstream.

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

    .. change:: Fix KeyError when ClassVar exists on msgspec Struct
        :type: bugfix
        :pr: 4665

        Fix a bug in :class:`MsgspecDTO` where a KeyError was raised if a :class:`msgspec.Struct` contained a :class:`~typing.ClassVar`. ClassVars are now correctly skipped when generating field definitions.
