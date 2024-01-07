from typing import Any, Union


class SecretValue:
    """Represents a secret value that can be of type `str` or `bytes`."""

    def __init__(self, secret_value: Union[str, bytes]):
        """Initializes a SecretValue object with a secret value of type `str` or `bytes`.

        Args:
            secret_value (Union[str, bytes]): The secret value to be encapsulated.
        """

        self._secret_value = secret_value

    def get_value(self) -> Union[str, bytes]:
        """Returns the actual secret value.

        Returns:
            Union[str, bytes]: The secret value.
        """

        return self._secret_value

    def _get_hidden_value(self) -> Union[str, bytes]:
        """Return the hidden representation of the secret value.

        Raises:
            NotImplementedError: Always raised to enforce implementation in subclasses.
        """

        raise NotImplementedError("Subclasses must implement _get_hidden_value")

    def __len__(self) -> int:
        """Returns the length of the actual secret value.

        Returns:
            int: Length of the secret value.
        """

        return len(self.get_value())

    def __str__(self) -> str:
        """Returns a string representation of the hidden secret value.

        Returns:
            str: String representation of the hidden secret value.
        """

        return str(self._get_hidden_value())

    def __repr__(self) -> str:
        """Returns a string representation of the object for debugging purposes.

        Returns:
            str: String representation of the object.
        """

        class_name = self.__class__.__name__
        return f"{class_name}({self._get_hidden_value()!r})"

    def __eq__(self, other: Any) -> bool:
        """Checks if the given object is equal to the current instance.

        Args:
            other (Any): The object to compare.

        Returns:
            bool: True if equal, False otherwise.
        """

        return isinstance(other, self.__class__) and self.get_value() == other._secret_value

    def __hash__(self) -> int:
        """Returns the hash value of the actual secret value.

        Returns:
            int: Hash value of the secret value.
        """

        return hash(self.get_value())

    @staticmethod
    def _hide_value(value: Union[str, bytes]) -> str:
        """Hides the secret value.

        Args:
            value (Union[str, bytes]): The secret value to be hidden.

        Returns:
            str: The hidden representation of the secret value.
        """

        return "******" if value else ""


class SecretString(SecretValue):
    """Represents a secret string value."""

    def _get_hidden_value(self) -> str:
        """Overrides the base class method to return the hidden string value.

        Returns:
            str: The hidden string representation of the secret value.
        """

        return self._hide_value(self.get_value())


class SecretBytes(SecretValue):
    """Represents a secret bytes value."""

    def _get_hidden_value(self) -> bytes:
        """Overrides the base class method to return the hidden bytes value.

        Returns:
            bytes: The hidden bytes representation of the secret value.
        """

        return self._hide_value(self.get_value()).encode()
