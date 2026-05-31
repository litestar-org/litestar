==============
Flash 消息
==============

.. versionadded:: 2.7.0

Flash 消息是向用户传达信息的强大工具，例如通过一次性消息以及响应来显示成功通知、警告或错误，这些消息是由于某种用户操作而产生的。

它们通常用于在下一次页面加载时显示消息，是通过提供关于用户操作（如表单提交）的即时反馈来增强用户体验的好方法。

注册插件
----------------------

FlashPlugin 可以轻松与不同的模板引擎集成。
以下是如何将 ``FlashPlugin`` 注册到 ``Jinja2``、``Mako`` 和 ``MiniJinja`` 模板引擎的示例。

.. tab-set::

    .. tab-item:: Jinja2
        :sync: jinja

        .. literalinclude:: /examples/plugins/flash_messages/jinja.py
            :language: python
            :caption: 使用 Jinja2 模板引擎注册 flash 消息插件

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/plugins/flash_messages/mako.py
            :language: python
            :caption: 使用 Mako 模板引擎注册 flash 消息插件

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/plugins/flash_messages/minijinja.py
            :language: python
            :caption: 使用 MiniJinja 模板引擎注册 flash 消息插件

使用插件
----------------

在将 FlashPlugin 注册到应用程序后，您可以开始使用它在应用程序路由中添加和显示 flash 消息。

以下是一个示例，展示如何使用 FlashPlugin 与 Jinja2 模板引擎来显示 flash 消息。
同样的方法也适用于 Mako 和 MiniJinja 引擎。

.. literalinclude:: /examples/plugins/flash_messages/usage.py
    :language: python
    :caption: 使用 flash 消息插件与 Jinja2 模板引擎来显示 flash 消息

详细说明
+++++++++

#. 这里我们从 Litestar 包和相关插件导入所需的类和函数。
#. Flash 消息需要有效的会话配置，因此我们创建并启用 ``ServerSideSession`` 中间件。
#. 然后我们创建 ``TemplateConfig`` 和 ``FlashConfig`` 实例，分别设置模板引擎和 flash 消息的配置。
#. 使用 ``@get()`` 装饰器定义了一个名为 ``index`` 的单个路由处理程序。

   * 在此处理程序中，调用 ``flash`` 函数来添加新的 flash 消息。
     此消息存储在请求的上下文中，使其可供模板引擎在响应中呈现。
   * 该函数返回一个 ``Template`` 实例，其中 ``template_str``
     （阅读更多关于 :ref:`模板字符串 <usage/templating:template files vs. strings>` 的信息）
     包含内联 HTML 和 Jinja2 模板代码。
     此模板通过 Jinja2 for 循环遍历 flash 消息来动态显示它们。
     每条消息都包装在段落 (``<p>``) 标签中，显示消息内容及其类别。

#. 最后，创建一个 ``Litestar`` 应用程序实例，在其配置中指定 ``flash_plugin`` 和 ``index`` 路由处理程序。
   应用程序还配置了 ``template_config``，其中包括 ``Jinja2`` 模板引擎和模板目录的路径。
