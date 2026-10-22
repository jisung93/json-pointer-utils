"""json-pointer-utils: resolve and apply RFC 6901 JSON Pointers."""

from .core import (
    JSONPointerError,
    JSONPointerSyntaxError,
    JSONPointerResolutionError,
    resolve,
    get,
    set,
)

__all__ = [
    "JSONPointerError",
    "JSONPointerSyntaxError",
    "JSONPointerResolutionError",
    "resolve",
    "get",
    "set",
]
