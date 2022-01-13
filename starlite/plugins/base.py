from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from typing_extensions import Type


class AbstractBasePlugin(ABC):
    @abstractmethod
    def to_pydantic_model_class(self, model: Any) -> Type[BaseModel]:  # pragma: no cover
        raise NotImplementedError()

    @abstractmethod
    def from_pydantic_model_class(self, pydantic_model: Type[BaseModel]) -> Any:  # pragma: no cover
        raise NotImplementedError()
