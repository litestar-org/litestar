from typing import Any


class StarLiteException(Exception):
    detail: str

    def __init__(self, *args: Any, detail: str = "") -> None:
        """Base exception class from which all Starlite exceptions inherit.

        Args:
            *args (Any): args are cast to `str` before passing to `Exception.__init__()`
            detail (str, optional): detail of the exception.
        """
        self.detail = detail
        super().__init__(*(str(arg) for arg in args if arg), detail)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join(self.args).strip()


class MissingDependencyException(StarLiteException):
    """Missing optional dependency.

    This exception is raised only when a module depends on a dependency
    that has not been installed.
    """
