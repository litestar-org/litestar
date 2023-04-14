The TODO application
====================

Getting a list
--------------

The first thing we're going to set up for our app is a route handler that returns a
single TODO-list. A TODO-list in our case will be a list of dictionaries representing
the items on that list.

.. literalinclude:: get_todo_list.py
    :language: python
    :linenos:

If you run the app and visit http://127.0.0.1:8000/ in your browser you'll see the
following output:

.. figure:: get_todo_list.png

    Suddenly, JSON


Because we annotated our function with ``List[Dict[str, Union[str, bool]]]``, Litestar
infers that we want our data serialized as JSON:

.. literalinclude:: get_todo_list.py
    :language: python
    :lines: 6


Cleaning up the example with dataclasses
++++++++++++++++++++++++++++++++++++++++

Since these type annotations can become unwieldy quite easily, let's make our lives
simpler by using dataclasses instead:

.. literalinclude:: get_todo_list_dataclasses.py
    :language: python


This looks a lot cleaner and we have now the added benefit of being able to work with
dataclasses instead of plain dictionaries. The result will still be the same: Litestar
knows how to turn these dataclasses into JSON and will do so for us automatically.



Filtering the list using query parameters
-----------------------------------------

Currently our route handler will always return all items on our list. But what if we
are simply interested in those items that are done or not yet done?

For this we can employ query parameters.
