import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, Type, Union

from pydantic.types import UUID, Json

from starlite import MissingDependencyException
from starlite.plugins.base import PluginProtocol

try:
    from piccolo.columns import column_types
    from piccolo.table import Table, TableMetaclass
    from piccolo.utils.pydantic import create_pydantic_model
except ImportError as e:
    raise MissingDependencyException("tortoise-orm is not installed") from e

if TYPE_CHECKING:
    from pydantic import BaseModel

COLUMN_TYPE_MAP: Dict[Type[column_types.Column], Type[Any]] = {
    column_types.Float: float,
    column_types.Integer: int,
    column_types.Secret: str,
    column_types.Varchar: str,
    column_types.Text: str,
    column_types.UUID: UUID,
    column_types.Serial: int,
    column_types.BigInt: int,
    column_types.SmallInt: int,
    column_types.BigSerial: int,
    column_types.Timestamp: datetime.datetime,
    column_types.Timestamptz: datetime.datetime,
    column_types.Date: datetime.date,
    column_types.Time: datetime.time,
    column_types.Interval: datetime.timedelta,
    column_types.Boolean: bool,
    column_types.Numeric: Decimal,
    column_types.Decimal: Decimal,
    column_types.Real: float,
    column_types.DoublePrecision: float,
    column_types.JSON: Union[dict, list, Json],
    column_types.JSONB: Union[dict, list, Json],
    column_types.Bytea: bytes,
    column_types.Blob: bytes,
}


class PiccoloORMPlugin(PluginProtocol[Table]):
    _models_map: Dict[Type[Table], Type["BaseModel"]] = {}
    _data_models_map: Dict[Type[Table], Type["BaseModel"]] = {}

    def to_pydantic_model_class(self, model_class: Type[Table], **kwargs: Any) -> Type["BaseModel"]:
        """
        Given a tortoise model_class instance, convert it to a subclass of the tortoise "BaseModel"

        Since incoming request body's cannot and should not include values for
        related fields, pk fields and read only fields in tortoise-orm, we generate two different kinds of pydantic models here:
        - the first is a regular pydantic model, and the other is for the "data" kwarg only, which is further sanitized.

        This function uses memoization to ensure we don't recompute unnecessarily.
        """
        parameter_name = kwargs.get("parameter_name")
        if parameter_name == "data":
            if model_class not in self._data_models_map:
                self._data_models_map[model_class] = create_pydantic_model(
                    table=model_class, model_name=f"{model_class.__name__}RequestBody"
                )
            return self._data_models_map[model_class]
        if model_class not in self._models_map:
            self._models_map[model_class] = create_pydantic_model(
                table=model_class, model_name=model_class.__name__, include_default_columns=True
            )
        return self._models_map[model_class]

    @staticmethod
    def is_plugin_supported_type(value: Any) -> bool:
        """
        Given a value of indeterminate type, determine if this value is supported by the plugin.
        """
        return isinstance(value, (Table, TableMetaclass))

    def from_pydantic_model_instance(self, model_class: Type[Table], pydantic_model_instance: "BaseModel") -> Table:
        """
        Given an instance of a pydantic model created using the plugin's 'to_pydantic_model_class',
        return an instance of the class from which that pydantic model has been created.

        This class is passed in as the 'model_class' kwarg.
        """
        return self.from_dict(model_class=model_class, **pydantic_model_instance.dict())

    def to_dict(self, model_instance: Table) -> Dict[str, Any]:
        """
        Given an instance of a model supported by the plugin, return a dictionary of serializable values.
        """
        return model_instance.to_dict()

    def from_dict(self, model_class: Type[Table], **kwargs: Any) -> Table:
        """
        Given a class supported by this plugin and a dict of values, create an instance of the class
        """
        instance = model_class()
        for column in instance.all_columns():
            meta = column._meta  
            if meta.name in kwargs:
                setattr(instance, meta.name, kwargs[meta.name])
        return instance
