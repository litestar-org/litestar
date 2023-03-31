Building a DTO
==============

Custom DTO implementations can be built by inheriting from the :class:`AbstractDTOInterface <.dto.AbstractDTOInterface>`
class. The following example shows how to build a DTO that can be used to validate and convert data received from a
client request into a data structure that can be used to implement business logic.

In this example, we use SQLAlchemy ORM models to represent our application domain type, and msgspec to validate and
convert the raw client data.

.. literalinclude:: /examples/data_transfer_objects/building_a_dto.py
    :caption: building_a_dto.py
    :language: python
