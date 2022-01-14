from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel
from typing_extensions import Protocol, Type

if TYPE_CHECKING:
    from starlite.app import Starlite

T = TypeVar("T", contravariant=True)


class PluginProtocol(Protocol[T]):
    def __init__(self, app: "Starlite"):
        ...

    def to_pydantic_model_class(self, model_class: Type[T], **kwargs: Any) -> Type[BaseModel]:  # pragma: no cover
        """
        Given a model_class T, convert it to a pydantic model class
        """
        ...
