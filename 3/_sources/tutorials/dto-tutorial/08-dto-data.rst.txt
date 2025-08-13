Accessing the data
------------------

Sometimes, it doesn't make sense for data to be immediately parsed into an instance of the target class. We just saw an
example of this in the previous section, :ref:`read-only-fields`. When required fields are excluded from, or do not
exist in the client submitted data we will get an error upon instantiation of the class.

The solution to this is the :class:`DTOData <litestar.dto.data_structures.DTOData>` type.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/dto_data.py
   :language: python
   :linenos:
   :emphasize-lines: 6,26,28

The :class:`DTOData <litestar.dto.data_structures.DTOData>` type is a container for data that can be used to create instances,
and access the underlying parsed and validated data. In our latest adjustments, we import that from
``litestar.dto.factory``.

The handler function's data parameter type is changed to ``DTOData[Person]`` instead of ``Person``, and accordingly, the
value injected to represent the inbound client data will be an instance of
:class:`DTOData <litestar.dto.data_structures.DTOData>`.

In the handler, we produce a value for the ``id`` field, and create an instance of ``Person`` using the
:meth:`create_instance <litestar.dto.data_structures.DTOData.create_instance>` method of the ``DTOData`` instance.

And our app is back to a working state:

.. image:: images/dto_data.png
    :align: center

.. tip::
    To provide values for nested attributes you can use the "double-underscore" syntax as a keyword argument to the
    :meth:`create_instance() <litestar.dto.data_structures.DTOData.create_instance>` method. For example, ``address__id=1`` will
    set the ``id`` attribute of the ``address`` attribute of the created instance.

    See :ref:`dto-create-instance-nested-data` for more information.

The :class:`DTOData <litestar.dto.data_structures.DTOData>` type has some other useful methods, and we'll take a look at those
in the next section: :ref:`updating`.
