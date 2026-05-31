HTMX
====

Litestar `HTMX <https://htmx.org>`_ 集成。

HTMX 是一个 JavaScript 库，它使您可以直接在 HTML 中使用属性访问 AJAX、CSS Transitions、WebSockets 和服务器发送事件，因此您可以使用超文本的简单性和强大功能构建现代用户界面。

本节假设您具有 HTMX 的先验知识。
如果您想学习 HTMX，我们建议查阅他们的 `官方教程 <https://htmx.org/docs>`_。


HTMXPlugin
------------

Litestar 插件 ``HTMXPlugin`` 可用于轻松配置所有 Litestar 路由的默认请求类。

它可以通过 ``litestar[htmx]`` 包额外选项安装。

.. code-block:: python

    from litestar.plugins.htmx import HTMXPlugin
    from litestar import Litestar

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from pathlib import Path

    app = Litestar(
        route_handlers=[get_form],
        debug=True,
        plugins=[HTMXPlugin()],
        template_config=TemplateConfig(
            directory=Path("litestar_htmx/templates"),
            engine=JinjaTemplateEngine,
        ),
    )

有关可用属性的完整列表，请参阅 :class:`~litestar.plugins.htmx.HTMXDetails`。

HTMXRequest
------------

一个特殊的 :class:`~litestar.connection.Request` 类，提供与 HTMX 客户端的交互。您可以通过使用 ``HTMXPlugin`` 全局配置它，或者通过在任何路由、控制器、路由器或应用程序上设置 `request_class` 设置来配置。

.. code-block:: python

    from litestar.plugins.htmx import HTMXRequest, HTMXTemplate
    from litestar import get, Litestar
    from litestar.response import Template

    from litestar.contrib.jinja import JinjaTemplateEngine
    from litestar.template.config import TemplateConfig

    from pathlib import Path


    @get(path="/form")
    def get_form(request: HTMXRequest) -> Template:
        if request.htmx:  # 如果请求具有 "HX-Request" 头，则
            print(request.htmx)  # HTMXDetails 实例
            print(request.htmx.current_url)
        return HTMXTemplate(template_name="partial.html", context=context, push_url="/form")


    app = Litestar(
        route_handlers=[get_form],
        debug=True,
        request_class=HTMXRequest,
        template_config=TemplateConfig(
            directory=Path("litestar_htmx/templates"),
            engine=JinjaTemplateEngine,
        ),
    )

有关可用属性的完整列表，请参阅 :class:`~litestar.plugins.htmx.HTMXDetails`。


HTMX 响应类
---------------------


HTMXTemplate 响应类
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HTMX 最常见的用例是渲染 HTML 页面或 HTML 片段。Litestar 通过提供 :class:`~litestar.plugins.htmx.HTMXTemplate` 响应使这变得容易：

.. code-block:: python

    from litestar.plugins.htmx import HTMXTemplate
    from litestar.response import Template


    @get(path="/form")
    def get_form(
        request: HTMXRequest,
    ) -> Template:  # 返回类型是 Template 而不是 HTMXTemplate。
        ...
        return HTMXTemplate(
            template_name="partial.html",
            context=context,
            # 可选参数
            push_url="/form",  # 更新浏览器历史
            re_swap="outerHTML",  # 更改交换方法
            re_target="#new-target",  # 更改目标元素
            trigger_event="showMessage",  # 触发事件名称
            params={"alert": "Confirm your Choice."},  # 传递给事件的参数
            after="receive",  # 何时触发事件，
            # 可能的值为 'receive'、'settle' 和 'swap'
        )

.. note::
    - 返回类型是 litestar 的 ``Template`` 而不是 ``HTMXTemplate``。
    - ``trigger_event``、``params`` 和 ``after`` 参数彼此相关联。
    - 如果您要触发事件，则需要 ``after`` 并且它必须是 ``receive``、``settle`` 或 ``swap`` 之一。

HTMX 提供两种类型的响应 - 一种不允许对 DOM 进行更改，另一种允许。
Litestar 支持这两种：

1 - 不对 DOM 进行任何更改的响应
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 :class:`~litestar.plugins.htmx.HXStopPolling` 停止轮询响应。

.. code-block:: python

    @get("/")
    def handler() -> HXStopPolling:
        ...
        return HXStopPolling()

使用 :class:`~litestar.plugins.htmx.ClientRedirect` 通过页面重新加载进行重定向。

.. code-block:: python

    @get("/")
    def handler() -> ClientRedirect:
        ...
        return ClientRedirect(redirect_to="/contact-us")

使用 :class:`~litestar.plugins.htmx.ClientRefresh` 强制完整页面刷新。

.. code-block:: python

    @get("/")
    def handler() -> ClientRefresh:
        ...
        return ClientRefresh()

2 - 可能更改 DOM 的响应
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

使用 :class:`~litestar.plugins.htmx.HXLocation` 重定向到新位置而不重新加载页面。

.. note:: 此类提供更改 ``target``、``swapping`` 方法、发送的 ``values`` 和 ``headers`` 的能力。

.. code-block:: python

    @get("/about")
    def handler() -> HXLocation:
        ...
        return HXLocation(
            redirect_to="/contact-us",
            # 可选参数
            source,  # 请求的源元素。
            event,  # "触发"请求的事件。
            target="#target",  # 要定位的元素 id。
            swap="outerHTML",  # 要使用的交换方法。
            hx_headers={"attr": "val"},  # 传递给 HTMX 的头。
            values={"val": "one"},
        )  # 随响应提交的值。

使用 :class:`~litestar.plugins.htmx.PushUrl` 携带响应并将 URL 推送到浏览器，可选择更新 ``history`` 栈。

.. note:: 如果 ``push_url`` 的值设置为 ``False``，它将阻止更新浏览器历史记录。

.. code-block:: python

    @get("/about")
    def handler() -> PushUrl:
        ...
        return PushUrl(content="Success!", push_url="/about")

使用 :class:`~litestar.plugins.htmx.ReplaceUrl` 携带响应并替换浏览器 ``location`` 栏中的 URL。

.. note:: 如果 ``replace_url`` 的值设置为 ``False``，它将阻止更新浏览器的位置。

.. code-block:: python

    @get("/contact-us")
    def handler() -> ReplaceUrl:
        ...
        return ReplaceUrl(content="Success!", replace_url="/contact-us")

使用 :class:`~litestar.plugins.htmx.Reswap` 携带可能进行交换的响应。

.. code-block:: python

    @get("/contact-us")
    def handler() -> Reswap:
        ...
        return Reswap(content="Success!", method="beforebegin")

使用 :class:`~litestar.plugins.htmx.Retarget` 携带响应并更改目标元素。

.. code-block:: python

    @get("/contact-us")
    def handler() -> Retarget:
        ...
        return Retarget(content="Success!", target="#new-target")

使用 :class:`~litestar.plugins.htmx.TriggerEvent` 携带响应并触发事件。

.. code-block:: python

    @get("/contact-us")
    def handler() -> TriggerEvent:
        ...
        return TriggerEvent(
            content="Success!",
            name="showMessage",
            params={"attr": "value"},
            after="receive",  # 可能的值为 'receive'、'settle' 和 'swap'
        )
