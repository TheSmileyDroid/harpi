from __future__ import annotations

from typing import TypeVar, cast

T = TypeVar("T")


def get_nested_attr(
    obj: object,
    attr_chain: str,
    default: T,
) -> T:
    """Safely access nested attributes.

    Args:
        obj: The initial object.
        attr_chain (str): A dot-separated string of
            attribute names.
        default: Value to return if any attribute
            is None or does not exist.

    Returns:
        The nested attribute value or the default value.
    """
    try:
        for attr in attr_chain.split("."):
            obj = cast(T, getattr(obj, attr))
            if obj is None:
                return default
        return cast(T, obj)
    except AttributeError:
        return default
