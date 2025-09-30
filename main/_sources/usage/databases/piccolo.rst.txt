Piccolo ORM
===========

Piccolo ORM is an easy-to-use async ORM and query builder and Litestar
has a plugin called ``litestar-piccolo`` for working with this ORM.

Check out `the plugin docs <https://github.com/litestar-org/litestar-piccolo>`_
for more information about enabling the support.

.. note::
  Prior to removal in ``3.0.0`` we had ``piccolo`` bundled
  with the ``litestar`` itself.

  To migrate:
  - Use ``litestar[piccolo]`` installation extra
  - Use ``litestar_piccolo`` plugin
