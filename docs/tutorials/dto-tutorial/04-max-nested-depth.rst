Max nested depth
----------------

As we saw in the previous section, even though we didn't explicitly exclude the ``children`` from the nested
``Person.children`` representations, they were not included in the response.

Here's a reminder of the output:

.. image:: images/nested_collection_exclude.png
    :align: center

Given that we didn't explicitly exclude it from the response, each of the ``Person`` objects in the ``children``
collection should have an empty ``children`` collection. The reason they do not is due to
:attr:`max_nested_depth <litestar.dto.config.DTOConfig.max_nested_depth>` and its default value of ``1``.

The ``max_nested_depth`` attribute is used to limit the depth of nested objects that are
included in the response. In this case, the ``Person`` object has a ``children`` collection, which is a collection of
nested ``Person`` objects, so this represents a nested depth of 1. The ``children`` collections of the items in the
``Person.children`` collection are at a 2nd level of nesting, and so are excluded due to the default value of
``max_nested_depth``.

Let's now modify our script to include the children of children in the response:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/max_nested_depth.py
   :language: python
   :linenos:
   :emphasize-lines: 28

We now see those empty collections in our output:

.. image:: images/max_nested_depth.png
    :align: center

Now that we've seen how to use the ``max_nested_depth`` configuration, we'll revert to using the default value of ``1``
for the remainder of this tutorial.
