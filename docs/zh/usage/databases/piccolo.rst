Piccolo ORM
===========

Piccolo ORM 是一个易于使用的异步 ORM 和查询构建器，Litestar 有一个名为 ``litestar-piccolo`` 的插件用于与此 ORM 一起工作。

查看 `插件文档 <https://github.com/litestar-org/litestar-piccolo>`_ 以获取有关启用支持的更多信息。

.. note::
  在 ``3.0.0`` 中删除之前，我们将 ``piccolo`` 与 ``litestar`` 本身捆绑在一起。

  迁移方法：
  - 使用 ``litestar[piccolo]`` 安装额外包
  - 使用 ``litestar_piccolo`` 插件
