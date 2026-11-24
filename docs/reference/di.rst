di
--

.. automodule:: litestar.di
    :members:

.. py:currentmodule:: litestar.di

.. py:data:: NamedDependency

    Mark a parameter as a dependency resolved by *name*.

    Equivalent to ``Annotated[T, Dependency(kind="named")]``

.. py:data:: TypeDependency

    Mark a parameter as a dependency resolved by *type*.

    Equivalent to ``Annotated[T, Dependency(kind="type")]``

.. py:data:: DependencyKey
    :value: str | type[Any]

.. automodule:: litestar.di.exceptions
    :members:
    :exclude-members: __init__
