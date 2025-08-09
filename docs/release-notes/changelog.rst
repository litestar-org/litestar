:orphan:

3.x Changelog
=============
.. changelog:: 2.16.0
    :date: 2025-05-04

    .. change:: Logging: Selectively disable logging for status codes or exception types
        :type: feature
        :pr: 4086
        :issue: 4081


        Add support for disabling stack traces for specific status codes or exception
        types when in debug mode or running with ``log_exceptions="always"``

        .. code-block:: python
            :caption: Disable tracebacks for '404 - Not Found' exceptions

            from litestar import Litestar, get
            from litestar.logging import LoggingConfig

            app = Litestar(
                route_handlers=[index, value_error, name_error],
                logging_config=LoggingConfig(
                    disable_stack_trace={404},
                    log_exceptions="always",
                ),
            )


    .. change:: Reference route handler in error message for return value / status code mismatch
        :type: feature
        :pr: 4157

        Improve error message of :exc:`ImproperlyConfiguredException` raised when a
        route handler's return value annotation is incompatible with its status code.


    .. change:: DTO: Improve inspection and tracebacks for generated functions
        :type: feature
        :pr: 4159

        Generated transfer functions now populate :mod:`linecache`  to improve
        tracebacks and support introspection of the generated functions e.g. via
        :func:`inspect.getsource`

        **Before:**

        .. code-block:: text

            File "<string>", line 18, in func
            TypeError: <something's wrong>

        **After:**

        .. code-block:: text

            File "dto_transfer_function_0971e01f653c", line 18, in func
            TypeError: <something's wrong>


    .. change:: DTO: Add custom attribute accessor callable
        :type: feature
        :pr: 4160

        Add :attr:`~litestar.dto.base_dto.AbstractDTO.attribute_accessor` property to
        ``AbstractDTO``, that can be set to a custom :func:`getattr`\ -like function
        which will be used every time an attribute is accessed on a source instance


    .. change:: Typing: remove usage of private ``_AnnotatedAlias``
        :type: bugfix
        :pr: 4126

        Remove deprecated usage of ``_AnnotatedAlias``, which is no longer needed for
        backwards compatibility.

    .. change:: DI: Ensure generator dependencies always handle error during clean up
        :type: bugfix
        :pr: 4148

        Fix issue where dependency cleanup could be skipped during exception handling,
        if another exception happened during the cleanup itself.

        - Ensure all dependencies are cleaned up, even if exceptions occur.
        - Group exceptions using :exc:`ExceptionGroup` during cleanup phase.


    .. change:: CLI: Improve error message on ``ImportError``
        :type: bugfix
        :pr: 4152
        :issue: 4129

        Fix misleading error message when using ``--app`` CLI argument and an unrelated
        :exc:`ImportError` occurs. Unrelated import errors will now propagate as usual

    .. change:: CLI: Ensure dynamically added commands / groups are always visible
        :type: bugfix
        :pr: 4161
        :issue: 2783

        Fix an issue where dynamically added commands or groups were not always visible
        during listing e.g. via ``--help``

    .. change:: Testing: Ensure subprocess client does not swallow startup failure
        :type: bugfix
        :pr: 4153
        :issue: 4021

        Ensure ``StartupError`` is raised by
        :func:`~litestar.testing.subprocess_sync_client` and
        :func:`~litestar.testing.subprocess_async_client`
        if the application failed to start within the timeout.

    .. change:: OpenAPI: Use ``prefixItems`` for fixed-length tuples
        :type: bugfix
        :pr: 4132
        :issue: 4130

        Use ``prefixItems`` instead of ``array`` syntax to render fixed-length tuples


    .. change:: OpenAPI: Add custom example ids support
        :type: feature
        :pr: 4133
        :issue: 4013

        Add a new field ``id`` to :class:`~litestar.openapi.spec.Example`, to set a
        custom ID for examples

    .. change:: OpenAPI: Allow passing scalar configuration options
        :type: feature
        :pr: 4162
        :issue: 3951

        Add an ``options`` parameter to
        :class:`~litestar.openapi.plugins.ScalarRenderPlugin`, that can be used to pass
        options directly to scalar.

        .. code-block:: python

            from litestar import Litestar, get
            from litestar.openapi.config import OpenAPIConfig
            from litestar.openapi.plugins import ScalarRenderPlugin

            scalar_plugin = ScalarRenderPlugin(version="1.19.5", options={"showSidebar": False})

            app = Litestar(
                route_handlers=[hello_world],
                openapi_config=OpenAPIConfig(
                    title="Litestar Example",
                    description="Example of Litestar with Scalar OpenAPI docs",
                    version="0.0.1",
                    render_plugins=[scalar_plugin],
                    path="/docs",
                ),
            )


.. changelog:: 3.0.0
    :date: 2024-08-30

    .. change:: New stuff
        :type: feature
        :pr: 1234
        :breaking:

        This is a changelog entry
