Data Transfer Object (DTO)
==========================

.. mermaid::

        sequenceDiagram
            autonumber
            actor Client
            participant Litestar
            participant DTO
            actor Developer
            Client->>Litestar: Data as encoded bytes
            activate Litestar
            Litestar->>DTO: Encoded data
            deactivate Litestar
            activate DTO
            Note over DTO: Perform primitive type validation<br>and marshalling into data model
            DTO->>Developer: Data injected into handler
            deactivate DTO
            activate Developer
            Note over Developer: Developer receives data as type<br>declared in handler signature<br>and performs business logic
            Developer->>DTO: Data returned from handler
            deactivate Developer
            activate DTO
            Note over DTO: Data returned from the handler<br>marshalled into type that can be<br>encoded into bytes by Litestar
            DTO->>Litestar: Litestar encodable type
            deactivate DTO
            activate Litestar
            Note over Litestar: Data received from DTO<br>is encoded into bytes
            Litestar->>Client: Data as encoded bytes
            deactivate Litestar

Data movement
-------------

Data moves between each of the participants in the DTO chart, and as it does so, different actions are performed on the
data, and it takes different forms depending on the direction of data transfer, and the participants on either end of
the transfer. Lets take a look at each of these data movements:

Client -> Litestar -> DTO
~~~~~~~~~~~~~~~~~~~~~~~~~
TODO

DTO -> Developer
~~~~~~~~~~~~~~~~
TODO

Developer -> DTO
~~~~~~~~~~~~~~~~
TODO

DTO -> Litestar -> Client
~~~~~~~~~~~~~~~~~~~~~~~~~
TODO

Contents
--------

.. toctree::

    0-basic-use
    1-dto-factory
    2-dto-interface
