使用 SQLAlchemy 改进 TODO 应用
--------------------------------------

.. admonition:: 本教程适合谁?
    :class: info

    本教程面向已经熟悉 Litestar 核心概念(如路由处理器和依赖注入)的开发人员。

    如果你是 Litestar 新手,建议先学习 `开发基本 TODO 应用程序 <../todo-app>`_ 教程。

通过 Advanced Alchemy 安装 SQLAlchemy
========================================

要学习本教程,你需要安装 Advanced Alchemy。你可以使用 ``pip install advanced-alchemy[aiosqlite]`` 安装它,或者通过安装 ``sqlalchemy`` 额外包让 Litestar 为你安装(例如,``pip install 'litestar[standard,sqlalchemy]' aiosqlite``)。

.. note::
    Litestar 中的 SQLAlchemy 支持现在由 `Advanced Alchemy <https://docs.advanced-alchemy.litestar.dev/>`_ 提供,这是一个第一方库。所有导入都应使用 ``advanced_alchemy.extensions.litestar`` 而不是已弃用的 ``litestar.contrib.sqlalchemy`` 或 ``litestar.plugins.sqlalchemy`` 模块。

本教程包含什么内容?
========================

本教程基于 `TODO 应用教程 <../todo-app>`_,通过 Advanced Alchemy 使用 `SQLAlchemy <https://www.sqlalchemy.org/>`_ 添加数据库后端。

我们首先比较利用 SQLAlchemy 进行数据持久化的重构 TODO 应用与 `TODO 应用教程 <../todo-app>`_ 中的 TODO 应用。

然后,我们将通过利用更多 Litestar 的特性(如依赖注入和插件)逐步改进应用的设计。

目录
========

.. toctree::
    :titlesonly:

    0-introduction
    1-provide-session-with-di
    2-serialization-plugin
    3-init-plugin
    4-final-touches-and-recap
