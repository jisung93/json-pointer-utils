# json-pointer-utils

Resolve and apply RFC 6901 JSON Pointers against plain Python data structures, with zero third-party dependencies.

```python
from json_pointer_utils import resolve, get, set

doc = {"users": [{"name": "Ada"}, {"name": "Bob"}]}

assert resolve(doc, "/users/1/name") == "Bob"
assert get(doc, "/users/5/name", default=None) is None

doc2 = set(doc, "/users/0/name", "Augusta")
assert resolve(doc2, "/users/0/name") == "Augusta"
```

## Why this exists

`json-pointer-utils` exists to fill the gap between the standard library and
RFC 6901 for code that already manipulates plain dicts and lists. Python
ships JSON encoding and decoding, but nothing that understands the pointer
syntax (`/a/b`, `~0`, `~1`, `-`). This library parses that syntax and resolves
or applies it against Python-native structures.

The trade-off: `set()` is non-mutating. It returns a new document with shallow
copies along the affected path, leaving the original untouched. This favours
predictability over raw speed. If you need in-place mutation, copy the result
yourself or use a different library.

## Edge cases

- The empty pointer `""` denotes the whole document. Both `resolve` and `set`
  treat it that way.
- `-` in a list index means "past the last element". `set` uses it to append;
  `resolve` treats it as an error, because there is no element to read.
- `set` will **not** auto-create missing intermediate keys (`/a/b` against `{}`
  raises rather than producing `{"a": {"b": ...}}`). It also will not extend a
  list beyond its current length. These are deliberate: pointer-based
  application is not a schema-growth tool.
- `get` returns a `default` on resolution failures (missing keys, out-of-range
  indices) but still raises `JSONPointerSyntaxError` for malformed pointers.

## Exported names

`JSONPointerError`, `JSONPointerSyntaxError`, `JSONPointerResolutionError`,
`resolve`, `get`, `set`.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
