from __future__ import annotations

from typing import Generic, TypeVar

_SecretT = TypeVar("_SecretT", bound="str | bytes")


class SecretValue(Generic[_SecretT]):
    """Represents a secret value that can be of type `str` or `bytes`."""

    def __init__(self, secret_value: _SecretT) -> None:
        """Initializes a SecretValue object with a secret value of type `str` or `bytes`.

        Args:
            secret_value (str | bytes): The secret value to be encapsulated.
        """

        self._secret_value = secret_value

    def get_secret(self) -> _SecretT:
        """Returns the actual secret value.

        Returns:
            str | bytes: The secret value.
        """

        return self._secret_value

    def _get_obscured_representation(self) -> _SecretT:
        """Return the hidden representation of the secret value.

        Raises:
            NotImplementedError: Always raised to enforce implementation in subclasses.
        """

        raise NotImplementedError("Subclasses must implement _get_obscured_representation")

    def __len__(self) -> int:
        """Returns the length of the actual secret value.

        Returns:
            int: Length of the secret value.
        """

        return len(self.get_secret())

    def __str__(self) -> str:
        """Returns a string representation of the hidden secret value.

        Returns:
            str: String representation of the hidden secret value.
        """

        return str(self._get_obscured_representation())

    def __repr__(self) -> str:
        """Returns a string representation of the object for debugging purposes.

        Returns:
            str: String representation of the object.
        """

        class_name = self.__class__.__name__
        return f"{class_name}({self._get_obscured_representation()!r})"

    def __eq__(self, other: object) -> bool:
        """Checks if the given object is equal to the current instance.

        Args:
            other: The object to compare.

        Returns:
            bool: True if equal, False otherwise.
        """

        return isinstance(other, self.__class__) and self.get_secret() == other._secret_value

    def __hash__(self) -> int:
        """Returns the hash value of the actual secret value.

        Returns:
            int: Hash value of the secret value.
        """

        return hash(self.get_secret())


class SecretString(SecretValue[str]):
    """Represents a secret string value."""

    def _get_obscured_representation(self) -> str:
        """Overrides the base class method to return the hidden string value.

        Returns:
            str: The hidden string representation of the secret value.
        """

        return "******"


class SecretBytes(SecretValue[bytes]):
    """Represents a secret bytes value."""

    def _get_obscured_representation(self) -> bytes:
        """Overrides the base class method to return the hidden bytes value.

        Returns:
            bytes: The hidden bytes representation of the secret value.
        """

        return b"******"
