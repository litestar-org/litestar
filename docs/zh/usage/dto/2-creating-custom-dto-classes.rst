===============================
实现自定义 DTO 类
===============================

虽然 Litestar 维护一套 DTO 工厂，但可以创建自己的 DTO。
为此，您必须实现 :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` abc。

以下是协议方法的描述以及 Litestar 如何使用它们。
有关每个方法签名的详细信息，请参阅 :class:`参考文档 <litestar.dto.base_dto.AbstractDTO>`。

抽象方法
~~~~~~~~

这些方法必须在任何 :class:`AbstractDTO <litestar.dto.base_dto.AbstractDTO>` 子类型上实现。

``generate_field_definitions``
------------------------------

此方法接收 DTO 的模型类型，它应该返回一个生成器，
生成与模型字段对应的 :class:`DTOFieldDefinition<litestar.dto.data_structures.DTOFieldDefinition>` 实例。

``detect_nested_field``
-----------------------

此方法接收一个 :class:`FieldDefinition<litestar.typing.FieldDefinition>` 实例，
它应该返回一个布尔值，指示该字段是否是嵌套模型字段。
