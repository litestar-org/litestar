Excluding from nested models
----------------------------

The ``exclude`` option can be used to exclude fields from models that are related to our data model by using dotted
paths. For example, ``exclude={"a.b"}`` would exclude the ``b`` attribute of an instance nested on the ``a`` attribute.

To demonstrate, let's adjust our script to add an ``Address`` model, that is related to the ``Person`` model:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/nested_exclude.py
   :language: python
   :linenos:
   :emphasize-lines: 9-13,21,25,32,33

The ``Address`` model has three attributes, ``street``, ``city``, and ``country``, and we've added an ``address``
attribute to the ``Person`` model.

The ``ReadDTO`` class has been updated to exclude the ``street`` attribute of the nested ``Address`` model using the
dotted path syntax ``"address.street"``.

Inside the handler, we create an ``Address`` instance and assign it to the ``address`` attribute of the ``Person``.

When we call our handler, we can see that the ``street`` attribute is not included in the response:

.. image:: images/nested_exclude.png
    :align: center
