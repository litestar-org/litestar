Excluding from nested models
----------------------------

The ``exclude`` option can be used to exclude fields from models that are related to our data model. To demonstrate,
we now adjust our script to add an ``Address`` model, that is related to the ``Person`` model:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/nested_exclude.py
   :language: python
   :linenos:
