Data Transfer Object Tutorial
=============================

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/initial_pattern.py
    :language: python
    :caption: app.py

In the above script, a `Person` dataclass is defined representing a basic data structure with attributes for `name`,
`age`, and `email`.

A `create_person` route handler is defined that takes a `Person` object as ``data`` kwarg and returns the same object.
This works "out-of-the-box", that is, injecting dataclasses, and returning them from handlers is natively supported by
Litestar, so no additional configuration is required.

However, what if we want to restrict the information about users that we expose after they have been created. For
example, we may want to hide the user's email address from the response. This is where data transfer objects come in.

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_dto_example.py
    :language: python
    :caption: app.py
