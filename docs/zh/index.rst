:layout: landing
:description: Litestar 是一个功能强大、灵活、高性能且有明确主张的 ASGI 框架。

.. container::
    :name: home-head

    .. image:: https://raw.githubusercontent.com/litestar-org/branding/main/assets/Branding%20-%20SVG%20-%20Transparent/Badge%20-%20Blue%20and%20Yellow.svg
        :alt: Litestar 框架
        :width: 400
        :height: 400

    .. container::

        .. raw:: html

            <h1>Litestar</h1>

        .. container:: badges
           :name: badges

            .. image:: https://img.shields.io/github/actions/workflow/status/litestar-org/litestar/publish.yml?labelColor=202235&logo=github&logoColor=edb641
               :alt: GitHub Actions 最新发布工作流状态

            .. image:: https://img.shields.io/github/actions/workflow/status/litestar-org/litestar/ci.yml?labelColor=202235&logo=github&logoColor=edb641
               :alt: GitHub Actions CI 工作流状态

            .. image:: https://img.shields.io/github/actions/workflow/status/litestar-org/litestar/docs.yml?labelColor=202235&logo=github&logoColor=edb641
               :alt: GitHub Actions 文档构建工作流状态

            .. image:: https://img.shields.io/codecov/c/github/litestar-org/litestar?labelColor=202235&logo=codecov&logoColor=edb641
               :alt: 代码覆盖率

            .. image:: https://img.shields.io/pypi/v/litestar?labelColor=202235&color=edb641&logo=python&logoColor=edb641
               :alt: PyPI 版本

            .. image:: https://img.shields.io/github/all-contributors/litestar-org/litestar?labelColor=202235&color=edb641&logoColor=edb641
               :alt: 贡献者数量

            .. image:: https://img.shields.io/pypi/dm/litestar?logo=python&label=litestar%20downloads&labelColor=202235&color=edb641&logoColor=edb641
               :alt: PyPI 下载量

            .. image:: https://img.shields.io/pypi/pyversions/litestar?labelColor=202235&color=edb641&logo=python&logoColor=edb641
               :alt: 支持的 Python 版本

.. rst-class:: lead

   Litestar 框架支持 :doc:`/usage/plugins/index`，并内置了
   :doc:`依赖注入 </usage/dependency-injection>`、:doc:`安全原语 </usage/security/index>`、
   :doc:`OpenAPI 模式生成 </usage/openapi/index>`、`MessagePack <https://msgpack.org/>`_、
   :doc:`中间件 </usage/middleware/index>`、一个强大的 :doc:`CLI </usage/cli>` 体验等等。

.. container:: buttons

    :doc:`开始入门 <getting-started>`
    `使用文档 <usage>`_
    `API 文档 <reference>`_
    `博客 <https://blog.litestar.dev>`_

.. grid:: 1 1 2 3
    :padding: 0
    :gutter: 2

    .. grid-item-card:: :octicon:`repo` 教程
      :link: tutorials/index
      :link-type: doc

      针对 Litestar 常见用例和场景的逐步指南

    .. grid-item-card:: :octicon:`light-bulb` 主题
      :link: topics/index
      :link-type: doc

      讨论技术概念、设计理念和战略决策的文章。

    .. grid-item-card:: :octicon:`versions` 更新日志
      :link: release-notes/changelog
      :link-type: doc

      Litestar 框架的最新更新和增强功能。

    .. grid-item-card:: :octicon:`comment-discussion` 讨论
      :link: https://github.com/litestar-org/litestar/discussions

      参与讨论、提出问题或分享见解。

    .. grid-item-card:: :octicon:`issue-opened` 问题
      :link: https://github.com/litestar-org/litestar/issues

      报告问题或建议新功能。

    .. grid-item-card:: :octicon:`beaker` 贡献
      :link: contribution-guide
      :link-type: doc

      通过代码、文档等方式为 Litestar 的发展做出贡献。

赞助商
--------

.. rst-class:: lead

   Litestar 是一个社区驱动的开源项目，得益于我们赞助商的慷慨贡献而蓬勃发展，使我们能够追求创新发展并继续我们的使命，为用户提供卓越的工具和资源。


衷心感谢我们当前的赞助商：

.. container::
   :name: sponsors-section

   .. grid:: 3
      :class-row: surface
      :padding: 0
      :gutter: 2

      .. grid-item-card::
         :link: https://github.com/scalar/scalar

         .. image:: https://raw.githubusercontent.com/litestar-org/branding/main/assets/sponsors/scalar.svg
            :alt: Scalar.com
            :class: sponsor

         `Scalar.com <https://github.com/scalar/scalar>`_

      .. grid-item-card::
         :link: https://telemetrysports.com/

         .. image:: https://raw.githubusercontent.com/litestar-org/branding/main/assets/sponsors/telemetry-sports/unofficial-telemetry-whitebg.svg
            :alt: Telemetry Sports
            :class: sponsor

         `Telemetry Sports <https://telemetrysports.com/>`_

      .. grid-item-card::
         :link: https://www.stok.kr/

         .. image:: https://avatars.githubusercontent.com/u/144093421
            :alt: Stok
            :class: sponsor

         `Stok <https://www.stok.kr/>`_

我们邀请组织和个人加入我们的赞助计划。
通过在 `Polar <sponsor-polar_>`_、`GitHub <sponsor-github_>`_
和 `Open Collective <sponsor-oc_>`_ 等平台上成为赞助商，您可以在我们项目的发展中发挥关键作用。

除了常规赞助之外，我们还通过 `Polar <sponsor-polar_>`_ 参与基于承诺的赞助机会，
您可以为您希望看到实现的问题或功能承诺一定金额。


.. _sponsor-github: https://github.com/sponsors/litestar-org
.. _sponsor-oc: https://opencollective.com/litestar
.. _sponsor-polar: https://polar.sh/litestar-org

.. toctree::
    :titlesonly:
    :caption: 文档
    :hidden:

    getting-started
    usage/index
    reference/index
    benchmarks

.. toctree::
    :titlesonly:
    :caption: 指南
    :hidden:

    migration/index
    topics/index
    tutorials/index

.. toctree::
    :titlesonly:
    :caption: 贡献
    :hidden:

    contribution-guide
    可用问题 <https://github.com/search?q=user%3Alitestar-org+state%3Aopen+label%3A%22good+first+issue%22+++no%3Aassignee+&type=issues=>
    行为准则 <https://github.com/litestar-org/.github?tab=coc-ov-file#readme>
