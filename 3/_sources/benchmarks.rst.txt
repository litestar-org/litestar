Benchmarks
==========

Methodology
-----------

- Benchmarking is done using the
  `bombardier <https://github.com/codesenberg/bombardier>`__ benchmarking tool.
- Benchmarks are run on a dedicated machine, with a base Debian 11 installation.
- Each framework is contained within its own docker container, running on a dedicated
  CPU core (using the ``cset shield`` command and the ``--cpuset-cpus`` option for
  docker)
- Tests for the frameworks are written to make them as comparable as possible while
  completing the same tasks (you can see them
  `here <https://github.com/litestar-org/api-performance-tests/tree/main/frameworks>`__)
- Each application is run using `uvicorn <https://www.uvicorn.org/>`__ with
  **one worker** and `uvloop <https://uvloop.readthedocs.io/>`__
- Test data has been randomly generated and is being imported from a shared module
- All frameworks are used with their "stock" configuration, i.e. without applying any
  additional optimizations. All tests have been written according to the respective
  official documentation, applying the practices shown there

Results
-------

..  note::
    If a result is missing for a specific framework that means either

    - The framework does not support this functionality (this will be mentioned in the
      test description)
    - More than 0.1% of responses were dropped

JSON
~~~~

Serializing a dictionary into JSON

.. figure:: /images/benchmarks/rps_json.svg
   :alt: RPS JSON

   RPS JSON

.. note::
    Because all frameworks are being used in their "stock" configuration, Litestar will
    run the data through `msgspec <https://jcristharif.com/msgspec/>`_ and FastAPI
    through `Pydantic <https://docs.pydantic.dev/latest/>`_


Serialization
~~~~~~~~~~~~~

Serializing Pydantic models and dataclasses into JSON

.. figure:: /images/benchmarks/rps_serialization.svg
   :alt: RPS serializing Pydantic models and dataclasses into JSON

   RPS serializing Pydantic models and dataclasses into JSON


Files
~~~~~

.. figure:: /images/benchmarks/rps_files.svg
   :alt: RPS files

   RPS files

.. note::
    Synchronous file responses are not / only partially supported for Sanic and Quart


Path and query parameter handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*All responses return “No Content”*

-  No params: No path parameters
-  Path params: Single path parameter, coerced into an integer
-  Query params: Single query parameter, coerced into an integer
-  Mixed params: A path and a query parameters, coerced into integers

.. figure:: /images/benchmarks/rps_params.svg
   :alt: RPS path and query parameters

   RPS path and query parameters

Dependency injection
~~~~~~~~~~~~~~~~~~~~

-  Resolving 3 nested synchronous dependencies
-  Resolving 3 nested asynchronous dependencies (only supported by ``Litestar`` and ``FastAPI``)
-  Resolving 3 nested synchronous, and 3 nested asynchronous dependencies (only supported by ``Litestar`` and ``FastAPI``)

.. figure:: /images/benchmarks/rps_dependency-injection.svg
   :alt: RPS Dependency injection

   RPS Dependency injection


.. note::
    Dependency injection is not supported by Starlette.


Plaintext
~~~~~~~~~

.. figure:: /images/benchmarks/rps_plaintext.svg
   :alt: RPS Plaintext

   RPS Plaintext

Interpreting the results
------------------------

An interpretation of these results should be approached with caution, as is the case for nearly all benchmarks.
A high score in a test does not necessarily translate to high performance of **your** application and **your** use case.
For almost any test you can probably write an app that performs better or worse at a comparable task **in your scenario**.

While trying to design the tests in a way that simulate somewhat realistic scenarios, they can never give an exact
representation of how a real world application behaves and performs, where, aside from the workload, many other factors
come into play. These tests were mainly written to be used internally for Litestar development, to help us locate and
track performance regressions and improvements.
