from typing import TYPE_CHECKING, Any, Dict, List, Type, cast

from pydantic_factories.utils import is_pydantic_model
from tortoise.fields import ReverseRelation
from tortoise.fields.relational import RelationalField

from starlite.exceptions import MissingDependencyException
from starlite.plugins.base import PluginProtocol

try:
    from tortoise import Model, ModelMeta
    from tortoise.contrib.pydantic import PydanticModel, pydantic_model_creator
except ImportError as e:
    raise MissingDependencyException("tortoise-orm is not installed") from e

if TYPE_CHECKING:
    from pydantic import BaseModel
    from typing_extensions import TypeGuard


class TortoiseORMPlugin(PluginProtocol[Model]):
    """Support (de)serialization and OpenAPI generation for Tortoise ORM
    types."""

    _models_map: Dict[Type[Model], Type[PydanticModel]] = {}
    _data_models_map: Dict[Type[Model], Type[PydanticModel]] = {}

    @staticmethod
    def _create_pydantic_model(model_class: Type[Model], **kwargs: Any) -> "Type[PydanticModel]":
        """Takes a tortoise model_class instance and convert it to a subclass
        of the tortoise PydanticModel.

        It fixes some issues with the result of the tortoise model
        creator.
        """
        pydantic_model = cast("Type[PydanticModel]", pydantic_model_creator(model_class, **kwargs))
        for (
            field_name,
            tortoise_model_field,
        ) in model_class._meta.fields_map.items():  # pylint: disable=protected-access
            if field_name in pydantic_model.__fields__:
                if (
                    is_pydantic_model(pydantic_model.__fields__[field_name].type_)
                    and "." in pydantic_model.__fields__[field_name].type_.__name__
                ):
                    sub_model_name = pydantic_model.__fields__[field_name].type_.__name__.split(".")[-2]
                    pydantic_model.__fields__[field_name].type_ = cast(
                        "Type[PydanticModel]", pydantic_model_creator(model_class, name=sub_model_name)
                    )
                if not tortoise_model_field.required:
                    pydantic_model.__fields__[field_name].required = False
                if tortoise_model_field.null:
                    pydantic_model.__fields__[field_name].allow_none = True
        return pydantic_model

    def to_pydantic_model_class(self, model_class: Type[Model], **kwargs: Any) -> Type[PydanticModel]:
        """Given a tortoise model_class instance, convert it to a subclass of
        the tortoise PydanticModel.

        Since incoming request body's cannot and should not include values for
        related fields, pk fields and read only fields in tortoise-orm, we generate two different kinds of pydantic models here:
        - the first is a regular pydantic model, and the other is for the "data" kwarg only, which is further sanitized.

        This function uses memoization to ensure we don't recompute unnecessarily.
        """
        parameter_name = kwargs.pop("parameter_name", None)
        if parameter_name == "data":
            if model_class not in self._data_models_map:
                fields_to_exclude: List[str] = [
                    field_name
                    for field_name, tortoise_model_field in model_class._meta.fields_map.items()  # pylint: disable=protected-access
                    if isinstance(tortoise_model_field, (RelationalField, ReverseRelation)) or tortoise_model_field.pk
                ]
                kwargs.update(
                    exclude=tuple(fields_to_exclude), exclude_readonly=True, name=f"{model_class.__name__}RequestBody"
                )
                self._data_models_map[model_class] = self._create_pydantic_model(model_class=model_class, **kwargs)
            return self._data_models_map[model_class]
        if model_class not in self._models_map:
            kwargs.update(name=model_class.__name__)
            self._models_map[model_class] = self._create_pydantic_model(model_class=model_class, **kwargs)
        return self._models_map[model_class]

    @staticmethod
    def is_plugin_supported_type(value: Any) -> "TypeGuard[Model]":
        """Given a value of indeterminate type, determine if this value is
        supported by the plugin."""
        return isinstance(value, (Model, ModelMeta))

    def from_pydantic_model_instance(self, model_class: Type[Model], pydantic_model_instance: "BaseModel") -> Model:
        """Given an instance of a pydantic model created using the plugin's
        'to_pydantic_model_class', return an instance of the class from which
        that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.
        """
        return model_class().update_from_dict(pydantic_model_instance.dict())

    async def to_dict(self, model_instance: Model) -> Dict[str, Any]:  # pylint: disable=invalid-overridden-method
        """Given an instance of a model supported by the plugin, return a
        dictionary of serializable values."""
        pydantic_model_class = self.to_pydantic_model_class(type(model_instance))
        data = await pydantic_model_class.from_tortoise_orm(model_instance)
        return cast("Dict[str, Any]", data.dict())

    def from_dict(self, model_class: Type[Model], **kwargs: Any) -> Model:
        """Given a class supported by this plugin and a dict of values, create
        an instance of the class."""
        return model_class().update_from_dict(**kwargs)
