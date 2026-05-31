数据传输对象 (DTO)
==========================

在 Litestar 中,数据传输对象(DTO)是一个用于控制从客户端流入的数据转换为开发人员在其处理器中使用的有用形式,然后再返回的类。

下图演示了在 Litestar 中单个请求上下文中如何使用 DTO:


.. mermaid::

        sequenceDiagram
            autonumber
            actor Client
            participant Litestar
            participant DTO
            participant Handler
            Client->>Litestar: 编码字节形式的数据
            activate Litestar
            Litestar->>DTO: 编码数据
            deactivate Litestar
            activate DTO
            Note over DTO: 执行基本类型验证<br>并转换为数据模型
            DTO->>Handler: 数据注入到处理器
            deactivate DTO
            activate Handler
            Note over Handler: 处理器接收处理器签名中<br>声明的类型的数据<br>并执行业务逻辑
            Handler->>DTO: 从处理器返回的数据
            deactivate Handler
            activate DTO
            Note over DTO: 从处理器返回的数据<br>被转换为 Litestar<br>可以编码为字节的类型
            DTO->>Litestar: Litestar 可编码类型
            deactivate DTO
            activate Litestar
            Note over Litestar: 从 DTO 接收的数据<br>被编码为字节
            Litestar->>Client: 编码字节形式的数据
            deactivate Litestar

数据移动
-------------

以下是上图中每个参与者之间交互的简短摘要。

数据在 DTO 图表中的每个参与者之间移动,在移动过程中,对数据执行不同的操作,并且根据数据传输的方向和传输两端的参与者,它采用不同的形式。让我们看看每个数据移动:

客户端 → Litestar → DTO
~~~~~~~~~~~~~~~~~~~~~~~~~
- 从客户端以编码字节形式接收数据
- 在大多数情况下,未编码的字节直接传递给 DTO
- 例外是 multipart 和 URL 编码数据,在传递给 DTO 之前将其解码为 Python 内置类型

DTO → 处理器
~~~~~~~~~~~~~~~~
- DTO 从客户端接收数据
- 执行基本类型验证
- 将数据编组为处理器注解中声明的数据类型

处理器 → DTO
~~~~~~~~~~~~~~~~
- 处理器接收处理器签名中声明的类型的数据
- 开发人员执行业务逻辑并从处理器返回数据

DTO → Litestar
~~~~~~~~~~~~~~~~~~~~~~~~~
- DTO 从处理器接收数据
- 将数据编组为 Litestar 可以编码为字节的类型

Litestar → 客户端
~~~~~~~~~~~~~~~~~~
- 从 DTO 接收数据作为 Litestar 可以编码为字节的类型
- 数据被编码为字节并发送到客户端

目录
--------

.. toctree::

    0-basic-use
    1-abstract-dto
    2-creating-custom-dto-classes
