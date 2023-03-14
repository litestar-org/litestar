Starlite 2.0 migration guide
============================

.. py:currentmodule:: starlite


Changed module paths
---------------------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``1.50``                                           | ``2.x``                                                                |
+====================================================+========================================================================+
| **Datastructures**                                                                                                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.UploadFile``             | ``starlite.upload_file.UploadFile``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTask``                        | ``starlite.background_tasks.BackgroundTask``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTasks``                       | ``starlite.background_tasks.BackgroundTasks``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Configuration**                                                                                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AllowedHostsConfig``                    | ``starlite.config.allowed_hosts.AllowedHostsConfig``                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BaseLoggingConfig``                     | ``starlite.config.logging.BaseLoggingConfig``                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CacheConfig``                           | ``starlite.config.cache.CacheConfig``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CompressionConfig``                     | ``starlite.config.compression.CompressionConfig``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CORSConfig``                            | ``starlite.config.cors.CORSConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CSRFConfig``                            | ``starlite.config.csrf.CSRFConfig``                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.LoggingConfig``                         | ``starlite.config.logging.LoggingConfig``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StructLoggingConfig``                   | ``starlite.config.logging.StructLoggingConfig``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIConfig``                         | ``starlite.config.openapi.OpenAPIConfig``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StaticFilesConfig``                     | ``starlite.config.static_files.StaticFilesConfig``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TemplateConfig``                        | ``starlite.config.templates.TemplateConfig``                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Provide**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.datastructures.Provide``                | ``starlite.provide.Provide``                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Pagination**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncClassicPaginator``         | ``starlite.utils.pagination.AbstractAsyncClassicPaginator``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncCursorPaginator``          | ``starlite.utils.pagination.AbstractAsyncCursorPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAsyncOffsetPaginator``          | ``starlite.utils.pagination.AbstractAsyncOffsetPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncClassicPaginator``          | ``starlite.utils.pagination.AbstractSyncClassicPaginator``             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncCursorPaginator``           | ``starlite.utils.pagination.AbstractSyncCursorPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSyncOffsetPaginator``           | ``starlite.utils.pagination.AbstractSyncOffsetPaginator``              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ClassicPagination``                     | ``starlite.utils.pagination.ClassicPagination``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CursorPagination``                      | ``starlite.utils.pagination.CursorPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OffsetPagination``                      | ``starlite.utils.pagination.OffsetPagination``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Response containers**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.File``                                  | ``starlite.response_containers.File``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Redirect``                              | ``starlite.response_containers.Redirect``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseContainer``                     | ``starlite.response_containers.ResponseContainer``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Stream``                                | ``starlite.response_containers.Stream``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Template``                              | ``starlite.response_containers.Template``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Exceptions**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HTTPException``                         | ``starlite.exceptions.HTTPException``                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImproperlyConfiguredException``         | ``starlite.exceptions.ImproperlyConfiguredException``                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.InternalServerException``               | ``starlite.exceptions.InternalServerException``                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MissingDependencyException``            | ``starlite.exceptions.MissingDependencyException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NoRouteMatchFoundException``            | ``starlite.exceptions.NoRouteMatchFoundException``                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotAuthorizedException``                | ``starlite.exceptions.NotAuthorizedException``                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotFoundException``                     | ``starlite.exceptions.NotFoundException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.PermissionDeniedException``             | ``starlite.exceptions.PermissionDeniedException``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ServiceUnavailableException``           | ``starlite.exceptions.ServiceUnavailableException``                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StarliteException``                     | ``starlite.exceptions.StarliteException``                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TooManyRequestsException``              | ``starlite.exceptions.TooManyRequestsException``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ValidationException``                   | ``starlite.exceptions.ValidationException``                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebSocketException``                    | ``starlite.exceptions.WebSocketException``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Testing**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TestClient``                            | ``starlite.testing.TestClient``                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AsyncTestClient``                       | ``starlite.testing.AsyncTestClient``                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_test_client``                    | ``starlite.testing.create_test_client``                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| **DTO**                                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DTOFactory``                            | ``starlite.dto.DTOFactory``                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIController``                     | ``starlite.openapi.controller.OpenAPIController``                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseSpec``                          | ``starlite.openapi.datastructures.ResponseSpec``                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Middleware**                                                                                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAuthenticationMiddleware``      | ``starlite.middleware.authentication.AbstractAuthenticationMiddleware``|
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AuthenticationResult``                  | ``starlite.middleware.authentication.AuthenticationResult``            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractMiddleware``                    | ``starlite.middleware.AbstractMiddleware``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DefineMiddleware``                      | ``starlite.middleware.DefineMiddleware``                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MiddlewareProtocol``                    | ``starlite.middleware.MiddlewareProtocol``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| **Security**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | ``starlite.security.AbstractSecurityConfig``                           |
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

            from starlite import ResponseHeader, get


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
