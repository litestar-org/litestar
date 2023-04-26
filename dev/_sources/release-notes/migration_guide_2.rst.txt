Litestar 2.0 migration guide
============================

.. py:currentmodule:: litestar


Changed module paths
---------------------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``1.50``                                           | ``2.x``                                                                |
+====================================================+========================================================================+
| **Datastructures**                                                                                                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.UploadFile``             | ``litestar.upload_file.UploadFile``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTask``                        | ``litestar.background_tasks.BackgroundTask``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTasks``                       | ``litestar.background_tasks.BackgroundTasks``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Configuration**                                                                                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AllowedHostsConfig``                    | ``litestar.config.allowed_hosts.AllowedHostsConfig``                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BaseLoggingConfig``                     | ``litestar.logging.BaseLoggingConfig``                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CacheConfig``                           | ``litestar.config.cache.CacheConfig``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CompressionConfig``                     | ``litestar.config.compression.CompressionConfig``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CORSConfig``                            | ``litestar.config.cors.CORSConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CSRFConfig``                            | ``litestar.config.csrf.CSRFConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.LoggingConfig``                         | ``litestar.logging.LoggingConfig``                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StructLoggingConfig``                   | ``litestar.logging.StructLoggingConfig``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIConfig``                         | ``litestar.openapi.OpenAPIConfig``                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StaticFilesConfig``                     | ``litestar.static_files.config.StaticFilesConfig``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TemplateConfig``                        | ``litestar.template.TemplateConfig``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Provide**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.Provide``                | ``litestar.provide.Provide``                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Pagination**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncClassicPaginator``         | ``litestar.utils.pagination.AbstractAsyncClassicPaginator``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncCursorPaginator``          | ``litestar.utils.pagination.AbstractAsyncCursorPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncOffsetPaginator``          | ``litestar.utils.pagination.AbstractAsyncOffsetPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncClassicPaginator``          | ``litestar.utils.pagination.AbstractSyncClassicPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncCursorPaginator``           | ``litestar.utils.pagination.AbstractSyncCursorPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncOffsetPaginator``           | ``litestar.utils.pagination.AbstractSyncOffsetPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ClassicPagination``                     | ``litestar.utils.pagination.ClassicPagination``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CursorPagination``                      | ``litestar.utils.pagination.CursorPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OffsetPagination``                      | ``litestar.utils.pagination.OffsetPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Response containers**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.File``                                  | ``litestar.response_containers.File``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Redirect``                              | ``litestar.response_containers.Redirect``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseContainer``                     | ``litestar.response_containers.ResponseContainer``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Stream``                                | ``litestar.response_containers.Stream``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Template``                              | ``litestar.response_containers.Template``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Exceptions**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HTTPException``                         | ``litestar.exceptions.HTTPException``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImproperlyConfiguredException``         | ``litestar.exceptions.ImproperlyConfiguredException``                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.InternalServerException``               | ``litestar.exceptions.InternalServerException``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MissingDependencyException``            | ``litestar.exceptions.MissingDependencyException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NoRouteMatchFoundException``            | ``litestar.exceptions.NoRouteMatchFoundException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotAuthorizedException``                | ``litestar.exceptions.NotAuthorizedException``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotFoundException``                     | ``litestar.exceptions.NotFoundException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.PermissionDeniedException``             | ``litestar.exceptions.PermissionDeniedException``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ServiceUnavailableException``           | ``litestar.exceptions.ServiceUnavailableException``                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StarliteException``                     | ``litestar.exceptions.StarliteException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TooManyRequestsException``              | ``litestar.exceptions.TooManyRequestsException``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ValidationException``                   | ``litestar.exceptions.ValidationException``                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebSocketException``                    | ``litestar.exceptions.WebSocketException``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Testing**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TestClient``                            | ``litestar.testing.TestClient``                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AsyncTestClient``                       | ``litestar.testing.AsyncTestClient``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_test_client``                    | ``litestar.testing.create_test_client``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **DTO**                                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DTOFactory``                            | ``litestar.dto.DTOFactory``                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIController``                     | ``litestar.openapi.controller.OpenAPIController``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseSpec``                          | ``litestar.openapi.datastructures.ResponseSpec``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Middleware**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAuthenticationMiddleware``      | ``litestar.middleware.authentication.AbstractAuthenticationMiddleware``|
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AuthenticationResult``                  | ``litestar.middleware.authentication.AuthenticationResult``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractMiddleware``                    | ``litestar.middleware.AbstractMiddleware``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DefineMiddleware``                      | ``litestar.middleware.DefineMiddleware``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MiddlewareProtocol``                    | ``litestar.middleware.MiddlewareProtocol``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Security**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | ``litestar.security.AbstractSecurityConfig``                           |
+----------------------------------------------------+------------------------------------------------------------------------+


Response headers
----------------

Response header can now be set using either a :class:`Sequence <typing.Sequence>` of
:class:`ResponseHeader <.datastructures.response_header.ResponseHeader>`, or by using a plain
:class:`Mapping[str, str] <typing.Mapping>`.
The typing of :class:`ResponseHeader <.datastructures.response_header.ResponseHeader>` was also changed to be more
strict and now only allows string values.


.. tab-set::

    .. tab-item:: 1.51

        .. code-block:: python

            from starlite import ResponseHeader, get


            @get(response_headers={"my-header": ResponseHeader(value="header-value")})
            async def handler() -> str:
                ...

    .. tab-item:: 2.x

        .. code-block:: python

            from litestar import ResponseHeader, get


            @get(response_headers=[ResponseHeader(name="my-header", value="header-value")])
            async def handler() -> str:
                ...


            # or


            @get(response_headers={"my-header": "header-value"})
            async def handler() -> str:
                ...


Response cookies
----------------

Response cookies might now also be set using a :class:`Mapping[str, str] <typing.Mapping>`, analogous to `Response headers`_.
