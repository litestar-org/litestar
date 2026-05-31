模板
==========

Litestar 内置支持 `Jinja2 <https://jinja.palletsprojects.com/en/3.0.x/>`_、`Mako <https://www.makotemplates.org/>`_ 和 `Minijinja <https://github.com/mitsuhiko/minijinja/tree/main/minijinja-py>`_ 模板引擎，以及抽象以使用您希望的任何模板引擎。

模板引擎
----------------

为了保持轻量级，Litestar 安装不包括 *Jinja*、*Mako* 或 *Minijinja* 库本身。在您可以开始使用它们之前，您必须通过相应的额外选项安装它：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: shell

            pip install 'litestar[jinja]'

    .. tab-item:: Mako
        :sync: mako

        .. code-block:: shell

            pip install 'litestar[mako]'

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: shell

            pip install 'litestar[minijinja]'

.. tip::

    *Jinja* 包含在 ``standard`` 额外选项中。如果您使用 ``litestar[standard]`` 安装了 Litestar，则无需显式添加 ``jinja`` 额外选项。


注册模板引擎
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

要注册内置模板引擎之一，您只需将其传递给 Litestar 构造函数：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/template_engine_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/template_engine_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/template_engine_minijinja.py
            :language: python

.. note::

    传递给 :class:`TemplateConfig <litestar.template.TemplateConfig>` 的 ``directory`` 参数可以是单个目录或用于加载模板的目录列表。

注册自定义模板引擎
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

上面的示例将创建一个 jinja Environment 实例，但您也可以传入自己的实例。

.. code-block:: python


    from litestar import Litestar
    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template import TemplateConfig
    from jinja2 import Environment, DictLoader

    my_custom_env = Environment(loader=DictLoader({"index.html": "Hello {{name}}!"}))
    app = Litestar(
        template_config=TemplateConfig(
            instance=JinjaTemplateEngine.from_environment(my_custom_env)
        )
    )

.. note::

    传递给 :class:`TemplateConfig <litestar.template.TemplateConfig>` 的 ``instance`` 参数不能与 ``directory`` 参数一起使用，如果选择使用 instance，您将完全负责引擎的创建。

定义自定义模板引擎
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

如果您希望使用其他模板引擎，可以通过实现 :class:`TemplateEngineProtocol <litestar.template.TemplateEngineProtocol>` 轻松做到。此类接受一个泛型参数，该参数应该是模板类，并且它指定了两个方法：

.. code-block:: python

   from typing import Protocol, Union, List
   from pydantic import DirectoryPath

   # 相应库的模板类
   from some_lib import SomeTemplate


   class TemplateEngineProtocol(Protocol[SomeTemplate]):
       def __init__(self, directory: Union[DirectoryPath, List[DirectoryPath]]) -> None:
           """构建模板引擎。"""
           ...

       def get_template(self, template_name: str) -> SomeTemplate:
           """加载具有 template_name 的模板并返回它。"""
           ...

一旦您有了自定义引擎，就可以像注册内置引擎一样注册它。

访问模板引擎实例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

如果您需要访问模板引擎实例，可以通过 :class:`TemplateConfig.engine <litestar.template.TemplateConfig>` 属性来完成：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/engine_instance_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/engine_instance_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/engine_instance_minijinja.py
            :language: python

模板响应
------------------

一旦您注册了模板引擎，就可以从路由处理程序返回 :class:`模板响应 <.response.Template>`：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/returning_templates_jinja.py
            :language: python

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/returning_templates_mako.py
            :language: python

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/returning_templates_minijinja.py
            :language: python

* ``name`` 是指定目录中的模板文件名。如果找不到具有该名称的文件，将引发 :class:`TemplateNotFoundException <.exceptions.TemplateNotFoundException>` 异常。
* ``context`` 是一个包含任意数据的字典，将传递给模板引擎的 ``render`` 方法。对于 Jinja 和 Mako，此数据将在 `模板上下文 <#template-context>`_ 中可用

模板文件 vs. 字符串
--------------------------

定义模板响应时，您可以传递模板文件名或包含模板的字符串。后者在您想要为小型模板或 :doc:`HTMX </usage/htmx>` 响应内联定义模板时很有用。

.. tab-set::

    .. tab-item:: 文件名

            .. code-block:: python
                :caption: 通过文件的模板

                @get()
                async def example() -> Template:
                    return Template(template_name="test.html", context={"hello": "world"})

    .. tab-item:: 字符串

            .. code-block:: python
                :caption: 通过字符串的模板

                @get()
                async def example() -> Template:
                    template_string = "{{ hello }}"
                    return Template(template_str=template_string, context={"hello": "world"})

模板上下文
----------------

`Jinja2 <https://jinja.palletsprojects.com/en/3.0.x/>`_ 和 `Mako <https://www.makotemplates.org/>`_ 都支持将上下文对象传递给模板以及定义将在模板内部可用的可调用对象。

访问请求实例
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

当前 :class:`Request <litestar.connection.request.Request>` 在模板上下文中的 ``request`` 下可用，它还提供对 :doc:`app 实例 </usage/applications>` 的访问。

例如，访问 ``app.state.key`` 看起来像这样：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: html

           <html>
               <body>
                   <div>
                       <span>My state value: {{request.app.state.some_key}}</span>
                   </div>
               </body>
           </html>


    .. tab-item:: Mako
        :sync: mako

        .. code-block:: html

           html
           <html>
               <body>
                   <div>
                       <span>My state value: ${request.app.state.some_key}</span>
                   </div>
               </body>
           </html>


    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: html

           <html>
               <body>
                   <div>
                       <span>My state value: {{request.app.state.some_key}}</span>
                   </div>
               </body>
           </html>


添加 CSRF 输入
^^^^^^^^^^^^^^^^^^

如果您想添加一个包含 `CSRF token <https://developer.mozilla.org/en-US/docs/Web/Security/Types_of_attacks#cross-site_request_forgery_csrf>`_ 的隐藏 ``<input>`` 标签，您首先需要配置 :ref:`CSRF 保护 <usage/middleware/builtin-middleware:csrf>`。完成后，现在可以在 HTML 表单内插入 CSRF 输入字段：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. code-block:: html

           <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           {{ csrf_input | safe }}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
           </html>

    .. tab-item:: Mako
        :sync: mako

        .. code-block:: html

           <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           ${csrf_input | n}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
           </html>

    .. tab-item:: MiniJinja
        :sync: minijinja

        .. code-block:: html

           <html>
               <body>
                   <div>
                       <form action="https://myserverurl.com/some-endpoint" method="post">
                           {{ csrf_input | safe}}
                           <label for="fname">First name:</label><br>
                           <input type="text" id="fname" name="fname">
                           <label for="lname">Last name:</label><br>
                           <input type="text" id="lname" name="lname">
                       </form>
                   </div>
               </body>
           </html>


输入将 CSRF token 作为其值保存，并且是隐藏的，因此用户无法看到或与之交互。当表单提交时，token 被发送回服务器，并由 CSRF 中间件检查。

.. note::

    必须将 `csrf_input` 标记为安全，以确保它不会被转义。

传递模板上下文
^^^^^^^^^^^^^^^^^^^^^^^^

将上下文传递给模板非常简单 - 它是 :class:`Template <litestar.response.Template>` 容器期望的 kwargs 之一，因此只需传递一个字符串键字典的值：

.. code-block:: python

   from litestar import get
   from litestar.response import Template


   @get(path="/info")
   def info() -> Template:
       return Template(template_name="info.html", context={"numbers": "1234567890"})


模板可调用对象
------------------

`Jinja2 <https://jinja.palletsprojects.com/en/3.0.x/>`_ 和 `Mako <https://www.makotemplates.org/>`_ 都允许用户定义在模板内部运行的自定义可调用对象。Litestar 在此基础上构建，并提供一些开箱即用的函数。

内置可调用对象
^^^^^^^^^^^^^^^^^^

``url_for``
    要访问路由处理程序的 URL，可以使用 ``url_for`` 函数。其签名和行为与 :meth:`route_reverse <litestar.app.Litestar.route_reverse>` 行为匹配。有关路由处理程序索引的更多详细信息，请参见 :ref:`这里 <usage/routing/handlers:route handler indexing>`。

``csrf_token``
    此函数返回请求的唯一 :ref:`CSRF token <usage/middleware/builtin-middleware:csrf>`。如果您希望将 ``csrf_token`` 插入非 HTML 模板，或者通过某些其他方式（例如在特殊的 ``<meta>`` 标签内）而不是使用隐藏输入字段将其插入 HTML 模板，可以使用此函数。

用于静态文件的 ``url_for``
    对于 :func:`~litestar.static_files.create_static_files_router` 提供的静态文件服务，``url_for`` 可以与 ``static`` 处理程序名称一起使用：``url_for("static", file_name="style.css")``



注册模板可调用对象
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:class:`TemplateEngineProtocol <litestar.template.base.TemplateEngineProtocol>` 指定了 ``register_template_callable`` 方法，允许在模板引擎上定义自定义可调用对象。此方法为两个内置引擎实现，可用于注册将注入模板的可调用对象。可调用对象应该期望一个参数 - 上下文字典。它可以是任何可调用对象 - 函数、方法或定义 call 方法的类。例如：

.. tab-set::

    .. tab-item:: Jinja
        :sync: jinja

        .. literalinclude:: /examples/templating/template_functions_jinja.py
            :caption: ``template_functions.py``
            :language: python

        .. literalinclude:: /examples/templating/templates/index.html.jinja2
            :language: html
            :caption: ``templates/index.html.jinja2``

    .. tab-item:: Mako
        :sync: mako

        .. literalinclude:: /examples/templating/template_functions_mako.py
            :caption: ``template_functions.py``
            :language: python

        .. literalinclude:: /examples/templating/templates/index.html.mako
            :language: html
            :caption: ``templates/index.html.mako``

    .. tab-item:: Minijinja
        :sync: minijinja

        .. literalinclude:: /examples/templating/template_functions_minijinja.py
            :caption: ``template_functions.py``
            :language: python

        .. literalinclude:: /examples/templating/templates/index.html.minijinja
            :language: html
            :caption: ``templates/index.html.minijinja``

使用 ``uvicorn template_functions:app`` 运行示例，访问 http://127.0.0.1:8000，您将看到

.. image:: /images/examples/template_engine_callable.png
    :alt: 模板引擎可调用对象示例
