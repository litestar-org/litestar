接收数据
--------------

到目前为止,我们只向客户端返回数据,然而,这只是故事的一半。我们还需要能够控制从客户端接收的数据。

这是我们将用于开始的代码:

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_receiving_data.py
   :language: python
   :linenos:

为了简化我们的演示,我们将数据模型简化回单个 ``Person`` 类,具有 ``name``、``age`` 和 ``email`` 属性。

和以前一样,``ReadDTO`` 为处理器配置,并从返回有效负载中排除 ``email`` 属性。

我们的处理器现在是一个 :class:`@post() <litestar.handlers.post>` 处理器,它被注解为接受并返回 ``Person`` 的实例。

Litestar 可以原生地将请求有效负载解码为 Python :func:`数据类 <dataclasses.dataclass>`,因此我们不需要为入站数据定义 DTO 来使此脚本工作。

现在我们需要向服务器发送数据来测试我们的程序,你可以使用像 `Postman <https://www.postman.com/>`_ 或 `Posting <https://github.com/darrenburns/posting?tab=readme-ov-file#posting>`_ 这样的工具。这是请求/响应有效负载的示例:

.. image:: images/simple_receive_data.png
    :align: center
