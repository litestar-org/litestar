from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from litestar.dto.factory import DTOConfig
    from litestar.dto.factory.data_structures import FieldDefinition
    from litestar.dto.factory.types import RenameStrategy


__all__ = ("determine_serialization_name",)


class RenameStrategies:
    """Useful renaming strategies than be used with :class:`DTOConfig`"""

    def __init__(self, renaming_strategy: RenameStrategy) -> None:
        self.renaming_strategy = renaming_strategy

    def __call__(self, field_name: str) -> str:
        if not isinstance(self.renaming_strategy, str):
            return self.renaming_strategy(field_name)

        return cast(str, getattr(self, self.renaming_strategy)(field_name))

    @staticmethod
    def upper(field_name: str) -> str:
        return field_name.upper()

    @staticmethod
    def lower(field_name: str) -> str:
        return field_name.lower()

    @staticmethod
    def camel(field_name: str) -> str:
        return RenameStrategies._camelize(field_name)

    @staticmethod
    def pascal(field_name: str) -> str:
        return RenameStrategies._camelize(field_name, capitalize_first_letter=True)

    @staticmethod
    def _camelize(string: str, capitalize_first_letter: bool = False) -> str:
        """Convert a string to camel case.

        Args:
            string (str): The string to convert
            capitalize_first_letter (bool): Default is False, a True value will convert to PascalCase
        Returns:
            str: The string converted to camel case or Pascal case
        """
        return "".join(
            word if index == 0 and not capitalize_first_letter else word.capitalize()
            for index, word in enumerate(string.split("_"))
        )


def determine_serialization_name(config: DTOConfig, field_definition: FieldDefinition) -> str:
    """Determine the serialization name strategy to use.

    Returns:
        RenameStrategies: The serialization name strategy to use.
    """
    if rename := config.rename_fields.get(field_definition.name):
        return rename
    if config.rename_strategy:
        return RenameStrategies(config.rename_strategy)(field_definition.name)
    return field_definition.name
