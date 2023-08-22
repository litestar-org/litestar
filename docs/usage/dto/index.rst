Data Transfer Object (DTO)
==========================

In Litestar, a Data Transfer Object (DTO) is a class that is used to control the flow of data from the client into a
useful form for the developer to use in their handler, and then back again.

The following diagram demonstrates how the DTO is used within the context of an individual request in Litestar:


.. mermaid::

        sequenceDiagram
            autonumber
            actor Client
            participant Litestar
            participant DTO
            participant Handler
            Client->>Litestar: Data as encoded bytes
            activate Litestar
            Litestar->>DTO: Encoded data
            deactivate Litestar
            activate DTO
            Note over DTO: Perform primitive type validation<br>and conversion into data model
            DTO->>Handler: Data injected into handler
            deactivate DTO
            activate Handler
            Note over Handler: Handler receives data as type<br>declared in handler signature<br>and performs business logic
            Handler->>DTO: Data returned from handler
            deactivate Handler
            activate DTO
            Note over DTO: Data returned from the handler<br>is converted into a type that <br>Litestar can encode into bytes
            DTO->>Litestar: Litestar encodable type
            deactivate DTO
            activate Litestar
            Note over Litestar: Data received from DTO<br>is encoded into bytes
            Litestar->>Client: Data as encoded bytes
            deactivate Litestar

Data movement
-------------

The following is a short summary of the interaction between each of the participants in the above diagram.

Data moves between each of the participants in the DTO chart, and as it does so, different actions are performed on the
data, and it takes different forms depending on the direction of data transfer, and the participants on either end of
the transfer. Lets take a look at each of these data movements:

Client → Litestar → DTO
~~~~~~~~~~~~~~~~~~~~~~~~~
- Data is received from the client as encoded bytes
- In most cases, the unencoded bytes are passed directly to the DTO
- Exception is multipart and URL encoded data, which is decoded into python built-in types before being passed to the
  DTO

DTO → Handler
~~~~~~~~~~~~~~~~
- DTO receives data from client
- Performs primitive type validation
- Marshals the data into the data type declared in the handler annotation

Handler → DTO
~~~~~~~~~~~~~~~~
- Handler receives data as type declared in handler signature
- Developer performs business logic and returns data from handler

DTO → Litestar
~~~~~~~~~~~~~~~~~~~~~~~~~
- DTO receives data from handler
- Marshals the data into a type that can be encoded into bytes by Litestar

Litestar → Client
~~~~~~~~~~~~~~~~~~
- Data is received from the DTO as a type that Litestar can encode into bytes
- Data is encoded into bytes and sent to the client

Contents
--------

.. toctree::

    0-basic-use
    1-abstract-dto
    2-creating-custom-dto-classes
