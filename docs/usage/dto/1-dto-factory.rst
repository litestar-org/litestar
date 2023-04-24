DTO Factory
===========

Litestar maintains a suite of DTO factory types that can be used to create DTOs for use with popular data modelling
libraries, such as ORMs. These take a model type as a generic type argument, and create subtypes of
:class:`AbstractDTOFactory <litestar.dto.factory.abc.AbstractDTOFactory>` that support conversion of that model type to
and from raw bytes.

The following factories are currently available:

- :class:`DataclassDTO <litestar.dto.factory.stdlib.DataclassDTO>`
- :class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>`

Using DTO Factories
-------------------

DTO factories are used to create DTOs for use with a particular data modelling library. The following example creates
a DTO for use with a SQLAlchemy model:

.. literalinclude:: /examples/data_transfer_objects/factory/simple_dto_factory_example.py
    :caption: A SQLAlchemy model DTO
    :language: python

Here we see that a SQLAlchemy model is used as both the ``data`` and return annotation for the handler, and while
Litestar does not natively support encoding/decoding to/from SQLAlchemy models, through
:class:`SQLAlchemyDTO <litestar.contrib.sqlalchemy.dto.SQLAlchemyDTO>` we can do this.

However, we do have some issues with the above example. Firstly, the user's password has been returned to them in the
response from the handler. Secondly, the user is able to set the ``created_at`` field on the model, which should only
ever be set once, and defined internally.

Lets explore how we can configure DTOs to manage these limitations.

Excluding fields
----------------

TODO

Marking fields
--------------

TODO

Renaming fields
---------------

TODO

Re-typing fields
----------------

TODO

Type checking
-------------

TODO - demonstrate error if DTO applied to handler not supported by factory subtype

Nested fields
-------------

TODO - demonstrate related/nested model data, and the ``max_nested_depth`` parameter
