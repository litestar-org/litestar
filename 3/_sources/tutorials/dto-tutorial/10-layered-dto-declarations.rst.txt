Declaring DTOs on app layers
-----------------------------

So far we've seen DTO declared per handler. Let's have a look at a script that declares multiple handlers - something
more typical of a real application.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/multiple_handlers.py
   :language: python
   :linenos:

DTOs can be defined on any :ref:`layer <layered-architecture>` of the application which gives us a chance to tidy up our
code a bit. Let's move the handlers into a controller and define the DTOs there.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/controller.py
   :language: python
   :linenos:
   :emphasize-lines: 30,31,44

The previous script had separate handler functions for each route, whereas the new script organizes these into a
``PersonController`` class, allowing us to move common configuration to the controller layer.

We have defined both ``dto=WriteDTO`` and ``return_dto=ReadDTO`` on the ``PersonController`` class, removing the need
to define these on each handler. We still define ``PatchDTO`` directly on the ``patch_person`` handler, to override the
controller level ``dto`` setting for that handler.
