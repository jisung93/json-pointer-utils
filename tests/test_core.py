import unittest

from json_pointer_utils import (
    JSONPointerError,
    JSONPointerResolutionError,
    JSONPointerSyntaxError,
    resolve,
    get,
    set,
)


class TestParseAndResolve(unittest.TestCase):
    def test_whole_document_empty_pointer(self):
        doc = {"a": 1}
        self.assertIs(resolve(doc, ""), doc)

    def test_simple_path(self):
        self.assertEqual(resolve({"a": {"b": 5}}, "/a/b"), 5)

    def test_list_index(self):
        self.assertEqual(resolve([10, 20, 30], "/1"), 20)

    def test_nested_list_and_object(self):
        doc = {"items": [{"id": 7}, {"id": 8}]}
        self.assertEqual(resolve(doc, "/items/1/id"), 8)

    def test_empty_string_key(self):
        self.assertEqual(resolve({"": "empty-key"}, "/"), "empty-key")

    def test_empty_string_key_nested(self):
        doc = {"": {"": 42}}
        self.assertEqual(resolve(doc, "//"), 42)

    def test_tilde_zero_decodes_tilde(self):
        self.assertEqual(resolve({"~": "v"}, "/~0"), "v")

    def test_tilde_one_decodes_slash(self):
        self.assertEqual(resolve({"a/b": "v"}, "/a~1b"), "v")

    def test_combined_escapes_in_one_token(self):
        # Token "~1~0" decodes to "/~".
        self.assertEqual(resolve({"/~": "v"}, "/~1~0"), "v")

    def test_dash_read_is_error(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve([1, 2], "/-")

    def test_missing_key_raises(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve({"a": 1}, "/b")

    def test_index_out_of_range(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve([1, 2], "/5")

    def test_indexing_scalar_raises(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve(5, "/a")

    def test_non_integer_list_index(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve([1, 2], "/x")

    def test_negative_list_index(self):
        with self.assertRaises(JSONPointerResolutionError):
            resolve([1, 2], "/-1")

    def test_pointer_not_starting_with_slash(self):
        with self.assertRaises(JSONPointerSyntaxError):
            resolve({}, "a/b")

    def test_pointer_must_be_string(self):
        with self.assertRaises(JSONPointerSyntaxError):
            resolve({}, 123)


class TestGet(unittest.TestCase):
    def test_get_returns_default_when_missing(self):
        self.assertIs(get({"a": 1}, "/b", None), None)

    def test_get_returns_explicit_default(self):
        sentinel = object()
        self.assertIs(get({}, "/x", sentinel), sentinel)

    def test_get_raises_when_no_default(self):
        with self.assertRaises(JSONPointerResolutionError):
            get({"a": 1}, "/b")

    def test_get_still_raises_on_syntax_error(self):
        with self.assertRaises(JSONPointerSyntaxError):
            get({}, "bad", None)

    def test_get_returns_value_when_present(self):
        self.assertEqual(get({"a": {"b": 9}}, "/a/b"), 9)


class TestSet(unittest.TestCase):
    def test_set_does_not_mutate_input(self):
        doc = {"a": {"b": 1}}
        result = set(doc, "/a/b", 2)
        self.assertEqual(doc["a"]["b"], 1)
        self.assertEqual(result["a"]["b"], 2)

    def test_set_existing_scalar(self):
        self.assertEqual(set({"a": 1}, "/a", 99), {"a": 99})

    def test_set_creates_new_key_at_leaf(self):
        self.assertEqual(set({}, "/x", 7), {"x": 7})

    def test_set_replaces_list_element(self):
        self.assertEqual(set([1, 2, 3], "/1", 99), [1, 99, 3])

    def test_set_appends_via_dash(self):
        self.assertEqual(set([1, 2], "/-", 3), [1, 2, 3])

    def test_set_whole_document(self):
        self.assertEqual(set("old", "", "new"), "new")

    def test_set_nested_existing_path(self):
        doc = {"a": {"b": {"c": 1}}}
        result = set(doc, "/a/b/c", 42)
        self.assertEqual(result["a"]["b"]["c"], 42)
        # Original untouched.
        self.assertEqual(doc["a"]["b"]["c"], 1)

    def test_set_cannot_auto_create_intermediate_key(self):
        with self.assertRaises(JSONPointerResolutionError):
            set({}, "/a/b", 1)

    def test_set_cannot_extend_list_beyond_length(self):
        with self.assertRaises(JSONPointerResolutionError):
            set([1, 2], "/5", 9)

    def test_set_dash_as_intermediate_token_is_error(self):
        with self.assertRaises(JSONPointerResolutionError):
            set([1, 2], "/-/x", 9)

    def test_set_into_scalar_raises(self):
        with self.assertRaises(JSONPointerResolutionError):
            set(5, "/a", 1)

    def test_set_shares_unaffected_branches(self):
        # Unaffected parts of the document should be the same objects.
        original = {"kept": [1, 2], "changed": {"x": 1}}
        result = set(original, "/changed/x", 2)
        self.assertIs(result["kept"], original["kept"])

    def test_set_preserves_list_type(self):
        result = set([1, 2], "/0", 9)
        self.assertIsInstance(result, list)

    def test_set_preserves_dict_type(self):
        result = set({"a": 1}, "/a", 2)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
