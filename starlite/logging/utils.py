from typing import Any, List


def resolve_handlers(handlers: List[Any]) -> List[Any]:
    """Converts list of string of handlers to the object of respective handler.

    Indexing the list performs the evaluation of the object.

    Args:
        handlers: An instance of 'ConvertingList'

    Returns:
        A list of resolved handlers.

    Notes:
        Due to missing typing in 'typeshed' we cannot type this as ConvertingList for now.
    """
    return [handlers[i] for i in range(len(handlers))]
