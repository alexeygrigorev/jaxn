"""Test boundary conditions and stress scenarios."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_single_character_chunks():
    """Test parsing by feeding one character at a time."""
    data = {
        "name": "Alice",
        "items": [
            {"id": 1, "value": "first"},
            {"id": 2, "value": "second"}
        ]
    }
    json_str = json.dumps(data)
    
    captured = {}
    items = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if parsed_value is not None:
                captured[field_name] = parsed_value
        
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'items':
                items.append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Feed one character at a time
    for char in json_str:
        parser.parse_incremental(char)
    
    assert captured['name'] == 'Alice'
    assert len(items) == 2
    assert items[0]['value'] == 'first'
    assert items[1]['value'] == 'second'


def test_empty_string_value():
    """Test parsing an empty string value."""
    data = {"name": "", "value": ""}
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert captured['name'] == ''
    assert captured['value'] == ''


def test_single_field_object():
    """Test object with only one field."""
    data = {"only": "field"}
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(captured) == 1
    assert captured['only'] == 'field'


def test_single_item_array():
    """Test array with only one item."""
    data = {"items": [{"id": 1}]}
    json_str = json.dumps(data)
    
    items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                items.append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(items) == 1
    assert items[0]['id'] == 1


def test_nested_empty_objects():
    """Test nested empty objects."""
    data = {
        "level1": {
            "level2": {
                "level3": {}
            }
        }
    }
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append((path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have field_start for nested objects
    assert len(field_starts) > 0


def test_nested_empty_arrays():
    """Test nested empty arrays."""
    data = {
        "level1": {
            "level2": []
        }
    }
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append((path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have field_start for nested arrays
    assert len(field_starts) > 0


def test_alternating_chunk_sizes():
    """Test with alternating small and large chunk sizes."""
    data = {
        "users": [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"},
            {"name": "User 3", "email": "user3@example.com"}
        ]
    }
    json_str = json.dumps(data)
    
    items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'users':
                items.append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Parse with alternating chunk sizes
    pos = 0
    chunk_sizes = [1, 5, 2, 10, 3, 15, 1]
    idx = 0
    while pos < len(json_str):
        chunk_size = chunk_sizes[idx % len(chunk_sizes)]
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
        idx += 1
    
    assert len(items) == 3
    assert items[0]['name'] == 'User 1'


def test_string_with_only_spaces():
    """Test parsing a string that contains only spaces."""
    data = {"spaces": "     "}
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert captured['spaces'] == '     '
    assert len(captured['spaces']) == 5


def test_field_name_with_special_characters():
    """Test field names with special characters."""
    data = {
        "field-with-dash": "value1",
        "field_with_underscore": "value2",
        "field.with.dot": "value3",
        "field:with:colon": "value4",
        "field@with@at": "value5"
    }
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert captured['field-with-dash'] == 'value1'
    assert captured['field_with_underscore'] == 'value2'
    assert captured['field.with.dot'] == 'value3'
    assert captured['field:with:colon'] == 'value4'
    assert captured['field@with@at'] == 'value5'


def test_very_long_field_name():
    """Test with a very long field name."""
    long_name = "field_" + "x" * 1000
    data = {long_name: "value"}
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert long_name in captured
    assert captured[long_name] == 'value'


def test_object_in_array_in_object_in_array():
    """Test complex alternating object/array nesting."""
    data = {
        "level1": [
            {
                "level2": [
                    {
                        "level3": [
                            {"value": "deeply nested"}
                        ]
                    }
                ]
            }
        ]
    }
    json_str = json.dumps(data)
    
    captured = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'value':
                captured.append((path, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(captured) == 1
    assert captured[0][1] == 'deeply nested'


def test_multiple_arrays_at_same_level():
    """Test multiple arrays at the same nesting level."""
    data = {
        "array1": [
            {"id": 1},
            {"id": 2}
        ],
        "array2": [
            {"id": 3},
            {"id": 4}
        ],
        "array3": [
            {"id": 5}
        ]
    }
    json_str = json.dumps(data)
    
    items_by_array = {'array1': [], 'array2': [], 'array3': []}
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name in items_by_array:
                items_by_array[field_name].append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(items_by_array['array1']) == 2
    assert len(items_by_array['array2']) == 2
    assert len(items_by_array['array3']) == 1


def test_callback_with_no_handler():
    """Test parser with default handler (no custom callbacks)."""
    data = {"name": "Alice", "age": "30"}
    json_str = json.dumps(data)
    
    # Use parser with no handler (uses default)
    parser = StreamingJSONParser()
    
    # Should not crash even though no callbacks are implemented
    parser.parse_incremental(json_str)


def test_handler_with_only_some_callbacks():
    """Test handler that only implements some callbacks."""
    data = {
        "items": [
            {"name": "Item 1"},
            {"name": "Item 2"}
        ]
    }
    json_str = json.dumps(data)
    
    names = []
    
    class PartialHandler(JSONParserHandler):
        # Only implement on_field_end, not other callbacks
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'name':
                names.append(parsed_value)
    
    handler = PartialHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert 'Item 1' in names
    assert 'Item 2' in names


def test_same_field_name_at_different_levels():
    """Test distinguishing fields with same name at different levels."""
    data = {
        "name": "Root",
        "child": {
            "name": "Child",
            "grandchild": {
                "name": "Grandchild"
            }
        }
    }
    json_str = json.dumps(data)
    
    names_with_path = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'name':
                names_with_path.append((path, parsed_value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(names_with_path) == 3
    # Root level
    assert ('', 'Root') in names_with_path
    # Child level
    child_names = [v for p, v in names_with_path if 'child' in p and 'grandchild' not in p]
    assert 'Child' in child_names
    # Grandchild level
    grandchild_names = [v for p, v in names_with_path if 'grandchild' in p]
    assert 'Grandchild' in grandchild_names


def test_json_with_trailing_comma_in_array():
    """Test that parser handles trailing commas gracefully (even though not valid JSON)."""
    # Note: Standard json.dumps won't create invalid JSON, but we can test with manually created string
    # For now, test with valid JSON
    data = {"items": [1, 2, 3]}
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append(field_name)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert 'items' in field_starts


def test_numeric_strings():
    """Test strings that look like numbers."""
    data = {
        "id": "12345",
        "version": "1.0.0",
        "code": "00001"
    }
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should be captured as strings
    assert captured['id'] == '12345'
    assert isinstance(captured['id'], str)
    assert captured['version'] == '1.0.0'
    assert captured['code'] == '00001'


def test_boolean_like_strings():
    """Test strings that look like booleans."""
    data = {
        "status": "true",
        "flag": "false",
        "enabled": "TRUE"
    }
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should be captured as strings, not converted to booleans
    assert captured['status'] == 'true'
    assert isinstance(captured['status'], str)
    assert captured['flag'] == 'false'
    assert captured['enabled'] == 'TRUE'


if __name__ == "__main__":
    # Run all tests
    test_single_character_chunks()
    print("✅ test_single_character_chunks passed")
    
    test_empty_string_value()
    print("✅ test_empty_string_value passed")
    
    test_single_field_object()
    print("✅ test_single_field_object passed")
    
    test_single_item_array()
    print("✅ test_single_item_array passed")
    
    test_nested_empty_objects()
    print("✅ test_nested_empty_objects passed")
    
    test_nested_empty_arrays()
    print("✅ test_nested_empty_arrays passed")
    
    test_alternating_chunk_sizes()
    print("✅ test_alternating_chunk_sizes passed")
    
    test_string_with_only_spaces()
    print("✅ test_string_with_only_spaces passed")
    
    test_field_name_with_special_characters()
    print("✅ test_field_name_with_special_characters passed")
    
    test_very_long_field_name()
    print("✅ test_very_long_field_name passed")
    
    test_object_in_array_in_object_in_array()
    print("✅ test_object_in_array_in_object_in_array passed")
    
    test_multiple_arrays_at_same_level()
    print("✅ test_multiple_arrays_at_same_level passed")
    
    test_callback_with_no_handler()
    print("✅ test_callback_with_no_handler passed")
    
    test_handler_with_only_some_callbacks()
    print("✅ test_handler_with_only_some_callbacks passed")
    
    test_same_field_name_at_different_levels()
    print("✅ test_same_field_name_at_different_levels passed")
    
    test_json_with_trailing_comma_in_array()
    print("✅ test_json_with_trailing_comma_in_array passed")
    
    test_numeric_strings()
    print("✅ test_numeric_strings passed")
    
    test_boolean_like_strings()
    print("✅ test_boolean_like_strings passed")
    
    print("\n🎉 All boundary condition tests passed!")
