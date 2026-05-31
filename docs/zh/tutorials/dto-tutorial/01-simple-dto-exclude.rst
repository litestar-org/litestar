我们的第一个 DTO
-------------
在本节中,我们将通过扩展脚本来创建我们的第一个 DTO,该脚本包括一个 DTO,确保我们不会在响应中暴露用户的电子邮件。

.. literalinclude:: /examples/data_transfer_objects/factory/tutorial/simple_dto_exclude.py
    :language: python
    :caption: ``app.py``
    :emphasize-lines: 6,16,17,20
    :linenos:

这里我们引入了一个新的 DTO 类(``ReadDTO``)并配置它来排除 ``Person.email`` 字段。路由处理器还被指示使用 DTO 来处理响应。

让我们更详细地查看这些更改。首先,我们添加两个额外的导入。

:class:`DTOConfig <litestar.dto.config.DTOConfig>` 类用于配置 DTO。在这种情况下,我们使用它从 DTO 中排除 ``email`` 字段,但还有许多其他配置选项可用,我们将在本教程中介绍其中的大部分。

:class:`DataclassDTO <litestar.dto.dataclass_dto.DataclassDTO>` 类是一个工厂类,专门从数据类创建 DTO。它也是一个 :class:`Generic <typing.Generic>` 类,这意味着它接受类型参数。当我们向泛型类提供类型参数时,它使该类成为泛型类的专用版本。在这种情况下,我们创建了一个 DTO 类型,专门用于在 ``Person`` 类的实例之间传输数据(``DataclassDTO[Person]``)。

.. note::

    不需要子类化 ``DataclassDTO`` 来创建专用的 DTO 类型。例如,``ReadDTO = DataclassDTO[Person]`` 也会创建一个有效的专用 DTO。但是,子类化 ``DataclassDTO`` 允许我们添加配置对象,以及专门化类型。

最后,我们指示路由处理器使用 DTO(``return_dto=ReadDTO``)从处理器响应传输数据。

让我们试一试,再次访问 `<http://localhost:8000/person/peter>`_,你应该看到以下响应:

.. image:: images/simple_exclude.png
    :align: center

这样更好,现在我们不会暴露用户的电子邮件地址!
