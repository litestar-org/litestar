=================
安全后端
=================

:class:`~.security.base.AbstractSecurityConfig`
-----------------------------------------------

:doc:`litestar.security </reference/security/index>` 包含一个 :class:`~.security.base.AbstractSecurityConfig` 类，
它作为 Litestar 提供的所有安全后端的基础，也旨在用作用户创建的自定义安全后端的基础，
您可以在这里阅读更多相关信息：
:doc:`/usage/security/abstract-authentication-middleware`

Session Auth 后端
------------------

Litestar 提供内置的 session auth 后端，可以与 Litestar session 中间件支持的任何
:ref:`session 后端 <usage/middleware/builtin-middleware:session middleware>` 一起开箱即用。

.. dropdown:: 点击查看使用 session auth 后端的示例

    .. literalinclude:: /examples/security/using_session_auth.py
        :language: python
        :caption: 使用 Session Auth

JWT Auth
--------

Litestar 包含多个 JWT 安全后端。查看
:doc:`JWT 文档 </usage/security/jwt>` 了解更多详细信息。
