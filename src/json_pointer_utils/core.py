"""Core implementation of RFC 6901 JSON Pointer resolution and application.

All functions operate on plain Python data structures composed of dict, list,
str, int, float, bool, and None. There are no third-party dependencies.
"""

from typing import Any, Iterator, List, Tuple, Union


__all__ = [
    "JSONPointerError",
    "JSONPointerSyntaxError",
    "JSONPointerResolutionError",
    "resolve",
    "get",
    "set",
]


class JSONPointerError(Exception):
    """Base class for all errors raised by this library."""


class JSONPointerSyntaxError(JSONPointerError):
    """Raised when a pointer string is not a syntactically valid RFC 6901 pointer."""


class JSONPointerResolutionError(JSONPointerError):
    """Raised when a valid pointer cannot be resolved against a document
    (e.g. a key is missing, a list index is out of range, or an attempt is
    made to index into a scalar)."""


_NO_DEFAULT = object()


def _unescape_reference_token(token: str) -> str:
    """Decode the tilde escapes of a single reference token.

    RFC 6901 section 4: '~1' represents '/' and '~0' represents '~'. The
    order of substitution matters: '~1' must be decoded before '~0',
    otherwise '/~1' would wrongly become '/~' and then '~'.
    """
    return token.replace("~1", "/").replace("~0", "~")


def _parse_pointer(pointer: str) -> List[str]:
    """Parse a pointer string into a list of decoded reference tokens.

    A leading '/' is the structural separator before each reference token;
    it is not part of the token itself. The empty string "" denotes the
    whole document and yields no tokens.
    """
    if not isinstance(pointer, str):
        raise JSONPointerSyntaxError(
            "pointer must be a string, got %r" % type(pointer).__name__
        )
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JSONPointerSyntaxError(
            "pointer must start with '/' or be empty: %r" % pointer
        )
    # An empty trailing token (e.g. "/a/") is permitted by the grammar and
    # represents the empty-string key in an object.
    parts = pointer.split("/")
    # Drop the leading empty element produced by the initial '/'.
    parts.pop(0)
    return [_unescape_reference_token(p) for p in parts]


def resolve(document: Any, pointer: str) -> Any:
    """Resolve ``pointer`` against ``document`` and return the referenced value.

    Raises JSONPointerSyntaxError for malformed pointers and
    JSONPointerResolutionError when the pointer cannot be resolved against
    the given document.
    """
    tokens = _parse_pointer(pointer)
    current: Any = document
    for i, token in enumerate(tokens):
        if isinstance(current, list):
            if token == "-":
                # Per RFC 6901, '-' refers to the element past the end of the
                # array. Resolving it on read is an error; it only has meaning
                # for set/append operations.
                raise JSONPointerResolutionError(
                    "'-' index refers past the end of array and cannot be read"
                )
            if token == "":
                raise JSONPointerResolutionError(
                    "empty token cannot index into a list"
                )
            try:
                index = int(token)
            except ValueError:
                raise JSONPointerResolutionError(
                    "list index must be an integer or '-', got %r" % token
                )
            if index < 0:
                raise JSONPointerResolutionError(
                    "list index must be non-negative, got %d" % index
                )
            if index >= len(current):
                raise JSONPointerResolutionError(
                    "list index %d out of range (len %d)"
                    % (index, len(current))
                )
            current = current[index]
        elif isinstance(current, dict):
            if token not in current:
                raise JSONPointerResolutionError(
                    "key %r not found" % token
                )
            current = current[token]
        else:
            raise JSONPointerResolutionError(
                "cannot index into %s with %r"
                % (type(current).__name__, token)
            )
    return current


def get(document: Any, pointer: str, default: Any = _NO_DEFAULT) -> Any:
    """Like resolve(), but returns ``default`` instead of raising
    JSONPointerResolutionError when the pointer is missing.

    A JSONPointerSyntaxError is still raised for malformed pointers, because a
    malformed pointer reflects a caller bug rather than a missing value.
    """
    try:
        return resolve(document, pointer)
    except JSONPointerResolutionError:
        if default is _NO_DEFAULT:
            raise
        return default


def set(root: Any, pointer: str, value: Any) -> Any:
    """Return a NEW document with ``pointer`` set to ``value``.

    The input ``root`` is never mutated; affected containers are shallow-copied
    along the path. This trade-off favours predictability over raw speed:
    callers never have to worry about aliasing, at the cost of copying the
    containers along the pointer path.
    """
    tokens = _parse_pointer(pointer)

    def _build(node: Any, depth: int) -> Any:
        if depth == len(tokens):
            return value
        token = tokens[depth]
        if isinstance(node, list):
            if token == "-":
                # Append semantics: append value beyond the last index.
                if depth == len(tokens) - 1:
                    return node + [value]
                # Append is not well-defined when there are deeper tokens to
                # descend into, because '-' points at a non-existent element.
                raise JSONPointerResolutionError(
                    "'-' cannot be used as an intermediate token on a list"
                )
            if token == "":
                raise JSONPointerResolutionError(
                    "empty token cannot index into a list"
                )
            try:
                index = int(token)
            except ValueError:
                raise JSONPointerResolutionError(
                    "list index must be an integer or '-', got %r" % token
                )
            if index < 0:
                raise JSONPointerResolutionError(
                    "list index must be non-negative, got %d" % index
                )
            if index >= len(node):
                # set() does not extend the list beyond its length; that
                # introduces surprising gaps and is outside the scope of a
                # pointer-based setter.
                raise JSONPointerResolutionError(
                    "list index %d out of range (len %d)"
                    % (index, len(node))
                )
            new_list = list(node)
            new_list[index] = _build(node[index], depth + 1)
            return new_list
        elif isinstance(node, dict):
            new_dict = dict(node)
            if token in node:
                new_dict[token] = _build(node[token], depth + 1)
            elif depth == len(tokens) - 1:
                new_dict[token] = value
            else:
                raise JSONPointerResolutionError(
                    "key %r not found and cannot be auto-created" % token
                )
            return new_dict
        else:
            raise JSONPointerResolutionError(
                "cannot index into %s with %r"
                % (type(node).__name__, token)
            )

    return _build(root, 0)
