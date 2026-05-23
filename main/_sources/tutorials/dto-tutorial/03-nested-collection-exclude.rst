Excluding from collections of nested models
-------------------------------------------

In Python, generic types can accept one or more type parameters (types that are enclosed in square brackets). This
pattern is often seen when representing a collection of some type, such as ``List[Person]``, where ``List`` is a
generic container type, and ``Person`` specializes the contents of the collection to contain only instances of the
``Person`` class.

Given a generic type, with an arbitrary number of type parameters (e.g., ``GenericType[Type0, Type1, ..., TypeN]``),
we use the index of the type parameter to indicate which type the exclusion should refer to. For example, ``a.0.b``,
excludes the ``b`` field from the first type parameter of ``a``, ``a.1.b`` excludes the ``b`` field from the second type
parameter of ``a``, and so on.

To demonstrate, lets add a self-referencing ``children`` relationship to our ``Person`` model:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/nested_collection_exclude.py
   :language: python
   :linenos:
   :emphasize-lines: 22,26,34,35,41

Now, a ``Person`` can have one or many ``children``, and each ``child`` can have one or many ``children``, and so on.

We have explicitly excluded the ``email`` and ``address`` fields of all represented ``children``
(``"children.0.email", "children.0.address"``).

In our handler we add ``children`` to the ``Person``, and each child has no ``children`` of their own.

Here's the output:

.. image:: images/nested_collection_exclude.png
    :align: center

Fantastic! Our ``children`` are now represented in the output, and their emails and addresses are excluded. However,
astute readers may have noticed that we didn't exclude the ``children`` field of ``Person.children``
(e.g., ``children.0.children``), yet that field is not represented in the output. To understand why, we'll next look at
the :attr:`max_nested_depth <litestar.dto.config.DTOConfig.max_nested_depth>` configuration option.
