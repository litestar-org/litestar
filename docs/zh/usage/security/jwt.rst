=====================
JWT 安全后端
=====================

Litestar 提供基于 JWT 的可选安全后端。要使用这些后端，请确保安装
`pyjwt <https://pyjwt.readthedocs.io/en/stable/>`_ 和 `cryptography <https://github.com/pyca/cryptography>`_
包，或者只需使用 ``jwt``
`extra <https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras>`_ 安装 Litestar：

.. code-block:: shell
    :caption: 使用 JWT extra 安装 Litestar

    pip install 'litestar[jwt]'

:class:`JWT Auth <.security.jwt.JWTAuth>` 后端
-----------------------------------------------

这是基础的 JWT Auth 后端。您可以在 :class:`~.security.jwt.JWTAuth` 中阅读其特定的 API。
它使用 header 发送 JWT 令牌 - 并且它期望请求使用相同的 header 键发送 JWT 令牌。

.. dropdown:: 点击查看代码

    .. literalinclude:: /examples/security/jwt/using_jwt_auth.py
        :language: python
        :caption: 使用 JWT Auth

:class:`JWT Cookie Auth <.security.jwt.JWTCookieAuth>` 后端
-----------------------------------------------------------

此后端继承自 :class:`~.security.jwt.JWTAuth` 后端，区别在于它使用 cookie 而不是使用 header 来传递 JWT 令牌。

.. dropdown:: 点击查看代码

    .. literalinclude:: /examples/security/jwt/using_jwt_cookie_auth.py
        :language: python
        :caption: 使用 JWT Cookie Auth

:class:`OAuth2 Bearer <.security.jwt.auth.OAuth2PasswordBearerAuth>` 密码流
---------------------------------------------------------------------------

:class:`~.security.jwt.auth.OAuth2PasswordBearerAuth` 后端继承自 :class:`~.security.jwt.JWTCookieAuth` 后端。
它的工作方式类似于 :class:`~.security.jwt.JWTCookieAuth` 后端，但用于 OAuth 2.0 Bearer 密码流。

.. dropdown:: 点击查看代码

    .. literalinclude:: /examples/security/jwt/using_oauth2_password_bearer.py
       :language: python
       :caption: 使用 OAUTH2 Bearer Password


使用自定义令牌类
----------------

可以通过创建 :class:`~.security.jwt.Token` 的子类并在后端上指定它来自定义使用的令牌类，
并添加任意字段：

.. literalinclude:: /examples/security/jwt/custom_token_cls.py
   :language: python
   :caption: 使用自定义令牌


令牌将从 JSON 转换为适当的类型，包括基本类型转换。

.. important::
    复杂的类型转换，特别是那些包括第三方库（如 Pydantic 或 attrs）的转换，
    以及任何自定义的 ``type_decoders`` 不可用于转换令牌。
    要支持更复杂的转换，必须在子类中重写
    :meth:`~.security.jwt.Token.encode` 和 :meth:`~.security.jwt.Token.decode` 方法。


验证发行者和受众
----------------

要验证 JWT ``iss``（*发行者*）和 ``aud``（*受众*）声明，可以在身份验证后端上设置接受的发行者或受众列表。
解码 JWT 时，令牌上的发行者或受众将与接受的发行者/受众列表进行比较。
如果令牌中的值与相应列表中的任何值都不匹配，将引发 :exc:`NotAuthorizedException`，
返回带有 ``401 Unauthorized`` 状态的响应。


.. literalinclude:: /examples/security/jwt/verify_issuer_audience.py
   :language: python
   :caption: 验证发行者和受众


自定义令牌验证
--------------

令牌解码/验证可以通过重写 :meth:`~.security.jwt.Token.decode_payload` 方法进一步自定义。
它将由 :meth:`~.security.jwt.Token.decode` 使用编码的令牌字符串调用，
并且必须返回一个表示解码有效负载的字典，然后由 :meth:`~.security.jwt.Token.decode`
使用该字典构造令牌类的实例。


.. literalinclude:: /examples/security/jwt/custom_decode_payload.py
   :language: python
   :caption: 自定义有效负载解码


使用令牌撤销
------------
令牌撤销可以通过维护已撤销令牌列表并在身份验证期间检查此列表来实现。
当令牌被撤销时，应将其添加到列表中，并且使用该令牌的任何后续请求都应被拒绝。

.. dropdown:: 点击查看代码

    .. literalinclude:: /examples/security/jwt/using_token_revocation.py
        :language: python
        :caption: 实现令牌撤销
