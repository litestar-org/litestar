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
| ``litestar.datastructures.UploadFile``             | ``litestar.upload_file.UploadFile``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.BackgroundTask``                        | ``litestar.background_tasks.BackgroundTask``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.BackgroundTasks``                       | ``litestar.background_tasks.BackgroundTasks``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Configuration**                                                                                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AllowedHostsConfig``                    | ``litestar.config.allowed_hosts.AllowedHostsConfig``                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.BaseLoggingConfig``                     | ``litestar.config.logging.BaseLoggingConfig``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.CacheConfig``                           | ``litestar.config.cache.CacheConfig``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.CompressionConfig``                     | ``litestar.config.compression.CompressionConfig``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.CORSConfig``                            | ``litestar.config.cors.CORSConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.CSRFConfig``                            | ``litestar.config.csrf.CSRFConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.LoggingConfig``                         | ``litestar.config.logging.LoggingConfig``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.StructLoggingConfig``                   | ``litestar.config.logging.StructLoggingConfig``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.OpenAPIConfig``                         | ``litestar.config.openapi.OpenAPIConfig``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.StaticFilesConfig``                     | ``litestar.config.static_files.StaticFilesConfig``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.TemplateConfig``                        | ``litestar.config.templates.TemplateConfig``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Provide**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.datastructures.Provide``                | ``litestar.provide.Provide``                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Pagination**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractAsyncClassicPaginator``         | ``litestar.utils.pagination.AbstractAsyncClassicPaginator``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractAsyncCursorPaginator``          | ``litestar.utils.pagination.AbstractAsyncCursorPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractAsyncOffsetPaginator``          | ``litestar.utils.pagination.AbstractAsyncOffsetPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractSyncClassicPaginator``          | ``litestar.utils.pagination.AbstractSyncClassicPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractSyncCursorPaginator``           | ``litestar.utils.pagination.AbstractSyncCursorPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractSyncOffsetPaginator``           | ``litestar.utils.pagination.AbstractSyncOffsetPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ClassicPagination``                     | ``litestar.utils.pagination.ClassicPagination``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.CursorPagination``                      | ``litestar.utils.pagination.CursorPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.OffsetPagination``                      | ``litestar.utils.pagination.OffsetPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Response containers**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.File``                                  | ``litestar.response_containers.File``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.Redirect``                              | ``litestar.response_containers.Redirect``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ResponseContainer``                     | ``litestar.response_containers.ResponseContainer``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.Stream``                                | ``litestar.response_containers.Stream``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.Template``                              | ``litestar.response_containers.Template``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Exceptions**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.HTTPException``                         | ``litestar.exceptions.HTTPException``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ImproperlyConfiguredException``         | ``litestar.exceptions.ImproperlyConfiguredException``                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.InternalServerException``               | ``litestar.exceptions.InternalServerException``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.MissingDependencyException``            | ``litestar.exceptions.MissingDependencyException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.NoRouteMatchFoundException``            | ``litestar.exceptions.NoRouteMatchFoundException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.NotAuthorizedException``                | ``litestar.exceptions.NotAuthorizedException``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.NotFoundException``                     | ``litestar.exceptions.NotFoundException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.PermissionDeniedException``             | ``litestar.exceptions.PermissionDeniedException``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ServiceUnavailableException``           | ``litestar.exceptions.ServiceUnavailableException``                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.LitestarException``                     | ``litestar.exceptions.LitestarException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.TooManyRequestsException``              | ``litestar.exceptions.TooManyRequestsException``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ValidationException``                   | ``litestar.exceptions.ValidationException``                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.WebSocketException``                    | ``litestar.exceptions.WebSocketException``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Testing**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.TestClient``                            | ``litestar.testing.TestClient``                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AsyncTestClient``                       | ``litestar.testing.AsyncTestClient``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.create_test_client``                    | ``litestar.testing.create_test_client``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **DTO**                                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.DTOFactory``                            | ``litestar.dto.DTOFactory``                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.OpenAPIController``                     | ``litestar.openapi.controller.OpenAPIController``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.ResponseSpec``                          | ``litestar.openapi.datastructures.ResponseSpec``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Middleware**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractAuthenticationMiddleware``      | ``litestar.middleware.authentication.AbstractAuthenticationMiddleware``|
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AuthenticationResult``                  | ``litestar.middleware.authentication.AuthenticationResult``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractMiddleware``                    | ``litestar.middleware.AbstractMiddleware``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.DefineMiddleware``                      | ``litestar.middleware.DefineMiddleware``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.MiddlewareProtocol``                    | ``litestar.middleware.MiddlewareProtocol``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Security**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``litestar.AbstractSecurityConfig``                | ``litestar.security.AbstractSecurityConfig``                           |
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

            from litestar import ResponseHeader, get


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
