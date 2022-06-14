import sys
from typing import Any, Union

from typing_extensions import get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType

    UNION_TYPES = {UnionType, Union}
else:
    UNION_TYPES = {Union}  # pragma: no cover


def detect_optional_union(annotation: Any) -> bool:
    """Given a type annotation determine if the annotation infers an optional union.

    >>> from typing import Optional, Union, get_args, get_origin
    >>> from types import UnionType
    >>> get_origin(Optional[int]) is Union
    True
    >>> get_origin(int | None) is UnionType
    True
    >>> get_origin(Union[int, None]) is Union
    True
    >>> get_args(Optional[int])
    (<class 'int'>, <class 'NoneType'>)
    >>> get_args(int | None)
    (<class 'int'>, <class 'NoneType'>)
    >>> get_args(Union[int, None])
    (<class 'int'>, <class 'NoneType'>)
    """
    return get_origin(annotation) in UNION_TYPES and type(None) in get_args(annotation)
