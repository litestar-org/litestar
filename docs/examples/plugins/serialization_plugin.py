from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from litestar import Litestar, post
from litestar.dto import DataclassDTO
from litestar.dto.base_dto import AbstractDTO
from litestar.plugins import SerializationPlugin
from litestar.typing import FieldDefinition


# Define a marker base class that we want to automatically serialize
@dataclass
class CustomModel:
    """Marker base class for models that should be auto-serialized."""


# Define some example models
@dataclass
class User(CustomModel):
    id: int
    name: str


@dataclass
class Product(CustomModel):
    id: int
    title: str
    price: float


class CustomSerializationPlugin(SerializationPlugin):
    """A plugin that provides automatic DTO creation for CustomModel subclasses."""

    def __init__(self) -> None:
        # Cache to avoid creating multiple DTOs for the same type
        self._type_dto_map: dict[type[CustomModel], type[DataclassDTO[Any]]] = {}

    def supports_type(self, field_definition: FieldDefinition) -> bool:
        """Check if the type is a CustomModel or collection of CustomModels.

        Args:
            field_definition: The parsed type annotation.

        Returns:
            True if the type is supported by this plugin.
        """
        return (
            field_definition.is_collection
            and field_definition.has_inner_subclass_of(CustomModel)
        ) or field_definition.is_subclass_of(CustomModel)

    def create_dto_for_type(
        self, field_definition: FieldDefinition
    ) -> type[AbstractDTO]:
        """Create a DTO for the given type.

        This method handles both single CustomModel instances and collections.
        It caches created DTOs to ensure the same DTO type is reused for the
        same model class.

        Args:
            field_definition: The parsed type annotation.

        Returns:
            A DTO class for the type.
        """
        # Get the actual model type, handling collections
        annotation = next(
            (
                inner_type.annotation
                for inner_type in field_definition.inner_types
                if inner_type.is_subclass_of(CustomModel)
            ),
            field_definition.annotation,
        )

        # Return cached DTO if we've already created one for this type
        if annotation in self._type_dto_map:
            return self._type_dto_map[annotation]

        # Create a new DTO type and cache it
        self._type_dto_map[annotation] = dto_type = DataclassDTO[annotation]  # type: ignore[valid-type]

        return dto_type


@post("/users", sync_to_thread=False)
def create_user(data: User) -> User:
    return data


@post("/products", sync_to_thread=False)
def create_product(data: Product) -> Product:
    return data


# The plugin automatically creates DTOs for User and Product
# because they inherit from CustomModel
app = Litestar(
    route_handlers=[create_user, create_product],
    plugins=[CustomSerializationPlugin()],
)
