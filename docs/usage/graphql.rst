Graphql
#######

Litestar does not support ``graphql`` out of the box. This can be done throught third party packages. 

.. note::
    Currently the only library that supports Litestar is `Strawberry <https://strawberry.rocks/docs/integrations/litestar#litestar>`_.
    Check the official `Graphql <https://graphql.org/community/tools-and-libraries/?tags=python>`_  documentation to learn more about other graphql libraries.


Installation
============

To get started simply install it with:


.. code-block:: shell

    pip install litestar[graphql]



Usage
=====

.. literalinclude:: /examples/graphql/simple_query.py
    :language: python
    :caption: Simple Graphql query



Now if you visit ``http://localhost:8000/movies``` you will see the ``graphiql`` web interface where you can interact with your endpoints.


Alternatively you can query your data by running the following in your terminal:

.. code-block:: shell

    curl 'http://localhost:8001/movies' -H 'content-type: application/json' --data '{ "query": "{ movies { title } }" }'


and see the following response:

.. code-block:: json

    {
    "data": {
        "movies": [
        {
            "title": "The Silent Storm"
        },
        {
            "title": "Whispers in the Wind"
        },
        {
            "title": "Echoes of Tomorrow"
        },
        {
            "title": "Fading Horizons"
        },
        {
            "title": "Broken Dreams"
        }
            ]
        }
    }


also: 

.. code-block:: shell
    
    curl 'http://localhost:8001/movies' -H 'content-type: application/json' --data '{ "query": "{ movies { director } }" }'


response:

.. code-block:: json

    {
    "data": {
        "movies": [
        {
            "director": "Ella Parker"
        },
        {
            "director": "Daniel Brooks"
        },
        {
            "director": "Sophia Rivera"
        },
        {
            "director": "Lucas Mendes"
        },
        {
            "director": "Amara Patel"
        }
        ]
    }
    }


