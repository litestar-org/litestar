=================================
排除和包含端点
=================================

请先阅读 :doc:`安全后端文档 </usage/security/security-backends>`，了解如何设置安全后端。
本节重点介绍为这些后端配置 ``exclude`` 规则。

有多种方法可以在身份验证流程中包含或排除端点。默认规则在所使用的 ``Auth`` 对象
（:class:`~.security.base.AbstractSecurityConfig` 的子类）中配置。下面的示例使用
:class:`~.security.session_auth.auth.SessionAuth`，但对于 :class:`~.security.jwt.auth.JWTAuth`
和 :class:`~.security.jwt.auth.JWTCookieAuth` 也是一样的。

排除路由
--------

``exclude`` 参数接受 :class:`字符串 <str>` 或 :class:`字符串列表 <str>`，
它们被解释为正则表达式模式。例如，下面的配置将对所有端点应用身份验证，
除了路由以 ``/login``、``/signup`` 或 ``/schema`` 开头的端点。
因此，不必也排除 ``/schema/swagger`` - 它包含在 ``/schema`` 模式中。

.. danger::

    传递 ``/`` 将禁用所有路由的身份验证，因为作为正则表达式，它匹配 *每个* 路径。

.. code-block:: python

    session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    # 我们必须为 session 后端传递配置。
    # 所有 session 后端都受支持
    session_backend_config=ServerSideSessionConfig(),
    # 排除任何不应该有身份验证的 URL。
    # 我们排除文档 URL、注册和登录。
    exclude=["/login", "/signup", "/schema"],
    )
    ...

包含路由
--------

由于排除规则被评估为正则表达式，因此可以传递一个反转排除的规则 - 这意味着，
除了模式中指定的路径外，没有其他路径将受到身份验证的保护。
在下面的示例中，只有 ``/secured`` 路由下的端点需要身份验证 - 所有其他路由都不需要。

.. code-block:: python

    ...
    session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    # 我们必须为 session 后端传递配置。
    # 所有 session 后端都受支持
    session_backend_config=ServerSideSessionConfig(),
    # 排除任何不应该有身份验证的 URL。
    # 我们排除文档 URL、注册和登录。
    exclude=[r"^(?!.*\/secured$).*$"],
    )
    ...

从身份验证中排除
----------------
有时，您可能希望对路由下的所有端点应用身份验证，但选择排除几个端点。
在这种情况下，您可以向路由处理器传递 ``exclude_from_auth=True``，如下所示。

.. code-block:: python

    ...
    @get("/secured")
    def secured_route() -> Any:
        ...

    @get("/unsecured", exclude_from_auth=True)
    def unsecured_route() -> Any:
        ...
    ...

您可以在安全配置中设置替代选项键，例如，您可以使用 ``no_auth`` 而不是 ``exclude_from_auth``。

.. code-block:: python

    ...
    @get("/secured")
    def secured_route() -> Any:
        ...

    @get("/unsecured", no_auth=True)
    def unsecured_route() -> Any:
        ...

    session_auth = SessionAuth[User, ServerSideSessionBackend](
    retrieve_user_handler=retrieve_user_handler,
    # 我们必须为 session 后端传递配置。
    # 所有 session 后端都受支持
    session_backend_config=ServerSideSessionConfig(),
    # 排除任何不应该有身份验证的 URL。
    # 我们排除文档 URL、注册和登录。
    exclude=["/login", "/signup", "/schema"],
    exclude_opt_key="no_auth"  # 默认值是 `exclude_from_auth`
    )
    ...
