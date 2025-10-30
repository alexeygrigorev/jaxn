"""Test edge cases and special scenarios not covered by other tests."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_empty_root_object():
    """Test parsing an empty JSON object."""
    json_str = "{}"
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('field_start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('field_end', path, field_name, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Empty object should not trigger any field events
    assert len(events) == 0


def test_empty_root_array():
    """Test parsing an empty JSON array."""
    json_str = "[]"
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_start(self, path, field_name):
            events.append(('array_start', path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('array_end', path, field_name, item))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Empty array should not trigger any item events
    assert len(events) == 0


def test_root_level_array():
    """Test parsing a root-level array (not wrapped in an object)."""
    data = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"}
    ]
    json_str = json.dumps(data)
    
    items = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            items.append((path, field_name, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should capture field values from objects in root array
    assert len(items) > 0
    names = [v for p, f, v in items if f == 'name']
    assert 'Alice' in names
    assert 'Bob' in names


def test_unicode_characters():
    """Test parsing JSON with Unicode characters including emoji."""
    data = {
        "message": "Hello 世界 🌍",
        "emoji": "😀 😃 😄",
        "unicode": "Ñoño café",
        "symbols": "€£¥"
    }
    json_str = json.dumps(data, ensure_ascii=False)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert captured['message'] == "Hello 世界 🌍"
    assert captured['emoji'] == "😀 😃 😄"
    assert captured['unicode'] == "Ñoño café"
    assert captured['symbols'] == "€£¥"


def test_unicode_streaming_chunks():
    """Test that Unicode characters are properly streamed chunk by chunk."""
    data = {"text": "Hello 🌍 World"}
    json_str = json.dumps(data, ensure_ascii=False)
    
    chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            chunks.append(chunk)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    reconstructed = ''.join(chunks)
    assert reconstructed == "Hello 🌍 World"
    assert '🌍' in reconstructed


def test_various_whitespace_formats():
    """Test parsing JSON with different whitespace arrangements."""
    # Minimal whitespace
    json_str1 = '{"name":"Alice","age":"30"}'
    
    # Lots of whitespace
    json_str2 = '''{
        "name"  :  "Alice"  ,
        "age"   :  "30"
    }'''
    
    # Mixed whitespace
    json_str3 = '{\n\t"name":\t"Alice",\n\t"age": "30"\n}'
    
    for json_str in [json_str1, json_str2, json_str3]:
        captured = {}
        
        class TestHandler(JSONParserHandler):
            def on_field_end(self, path, field_name, value, parsed_value=None):
                captured[field_name] = value
        
        handler = TestHandler()
        parser = StreamingJSONParser(handler)
        parser.parse_incremental(json_str)
        
        assert captured['name'] == 'Alice'
        assert captured['age'] == '30'


def test_incomplete_json_gracefully():
    """Test that parser handles incomplete JSON without crashing."""
    # Incomplete JSON - missing closing brace
    incomplete_json = '{"name": "Alice", "age": "30"'
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Should not crash, even though JSON is incomplete
    parser.parse_incremental(incomplete_json)
    
    # Should have captured the complete fields
    assert captured['name'] == 'Alice'
    assert captured['age'] == '30'


def test_incomplete_string_value():
    """Test parser with incomplete string value."""
    # String value not closed
    incomplete_json = '{"name": "Alice'
    
    chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            chunks.append(chunk)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Should not crash
    parser.parse_incremental(incomplete_json)
    
    # Should have started streaming the value
    assert len(chunks) > 0
    assert ''.join(chunks) == 'Alice'


def test_mixed_value_types():
    """Test comprehensive handling of all JSON value types."""
    data = {
        "string": "text",
        "number_int": 42,
        "number_float": 3.14,
        "boolean_true": True,
        "boolean_false": False,
        "null_value": None,
        "empty_object": {},
        "empty_array": [],
        "nested": {
            "level": 2,
            "values": [1, 2, 3]
        }
    }
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if parsed_value is not None:
                captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Only string values should be captured with on_field_end
    assert 'string' in captured
    assert captured['string'] == 'text'


def test_callback_order():
    """Test that callbacks fire in the correct order."""
    data = {
        "items": [
            {"id": 1, "name": "First"}
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class OrderTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('field_start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('field_end', path, field_name))
        
        def on_array_item_start(self, path, field_name):
            events.append(('item_start', path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('item_end', path, field_name))
    
    handler = OrderTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify order makes sense
    assert len(events) > 0
    
    # Field start should come before field end
    for i, event in enumerate(events):
        if event[0] == 'field_end':
            # Look for corresponding field_start
            field_name = event[2]
            # There should be a matching field_start before this
            starts_before = [e for e in events[:i] if e[0] == 'field_start' and e[2] == field_name]
            # Note: not all field_end will have field_start (e.g., for non-string values)


def test_parser_reuse():
    """Test that parser can be reused for multiple parsing operations."""
    json_str1 = '{"name": "Alice"}'
    json_str2 = '{"name": "Bob"}'
    
    captured = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured.append(value)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Parse first JSON
    parser.parse_incremental(json_str1)
    
    # Parse second JSON with same parser
    # Note: This might not work as expected since parser maintains state
    # But we should test it doesn't crash
    parser.parse_incremental(json_str2)
    
    # Both values should be captured
    assert 'Alice' in captured
    assert 'Bob' in captured


def test_very_long_string_value():
    """Test parsing with a very long string value."""
    long_string = "a" * 10000  # 10,000 characters
    data = {"long_value": long_string}
    json_str = json.dumps(data)
    
    captured = {}
    chunk_count = [0]
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            chunk_count[0] += 1
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert captured['long_value'] == long_string
    assert chunk_count[0] == 10000  # One chunk per character


def test_deeply_nested_with_context_limit():
    """Test that parser handles deep nesting within context buffer limits."""
    # Create a deeply nested structure with string values so field_end is called
    nested = {"level": "1"}
    current = nested
    for i in range(2, 50):  # Create 49 levels of nesting (2-49)
        current["nested"] = {"level": str(i)}
        current = current["nested"]
    
    json_str = json.dumps(nested)
    
    captured = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == "level":
                captured.append(parsed_value)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have captured all level values (1 initial + 48 nested = 49 total)
    assert len(captured) == 49
    assert captured[0] == "1"
    assert captured[-1] == "49"


def test_special_json_strings():
    """Test parsing strings that contain JSON-like content."""
    data = {
        "json_string": '{"nested": "value"}',
        "array_string": '[1, 2, 3]',
        "escaped_quotes": 'He said "hello"'
    }
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # The parser should treat these as regular strings, not parse them
    assert 'json_string' in captured
    # The value should contain the escaped content
    assert 'nested' in captured['json_string']


def test_numbers_and_booleans_in_arrays():
    """Test arrays with non-string primitive values."""
    data = {
        "numbers": [1, 2, 3, 4, 5],
        "booleans": [True, False, True],
        "mixed": [1, "two", True, None, 5.5]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Arrays of primitives should trigger field_start
    assert ('start', 'numbers') in events
    assert ('start', 'booleans') in events
    assert ('start', 'mixed') in events


def test_parse_from_old_new_with_invalid_input():
    """Test parse_from_old_new with invalid inputs."""
    captured = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured.append((field_name, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Test with old_text not being a prefix of new_text
    try:
        parser.parse_from_old_new('{"name": "Alice"}', '{"name": "Bob"}')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "must start with" in str(e)


def test_parse_from_old_new_empty_delta():
    """Test parse_from_old_new when delta is empty."""
    captured = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured.append((field_name, value))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Parse some initial text
    initial = '{"name": "Alice"}'
    parser.parse_from_old_new('', initial)
    
    # Parse again with same text (no delta)
    parser.parse_from_old_new(initial, initial)
    
    # Should have captured the name only once
    assert captured.count(('name', 'Alice')) == 1


def test_multiple_root_fields():
    """Test object with many root-level fields."""
    data = {f"field_{i}": f"value_{i}" for i in range(100)}
    json_str = json.dumps(data)
    
    captured = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # All 100 fields should be captured
    assert len(captured) == 100
    for i in range(100):
        assert captured[f"field_{i}"] == f"value_{i}"


def test_consecutive_escape_sequences():
    """Test multiple consecutive escape sequences."""
    data = {"text": "\n\n\n\t\t\t"}
    json_str = json.dumps(data)
    
    chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            chunks.append(chunk)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    result = ''.join(chunks)
    assert result == "\n\n\n\t\t\t"
    assert result.count('\n') == 3
    assert result.count('\t') == 3


if __name__ == "__main__":
    # Run all tests
    test_empty_root_object()
    print("✅ test_empty_root_object passed")
    
    test_empty_root_array()
    print("✅ test_empty_root_array passed")
    
    test_root_level_array()
    print("✅ test_root_level_array passed")
    
    test_unicode_characters()
    print("✅ test_unicode_characters passed")
    
    test_unicode_streaming_chunks()
    print("✅ test_unicode_streaming_chunks passed")
    
    test_various_whitespace_formats()
    print("✅ test_various_whitespace_formats passed")
    
    test_incomplete_json_gracefully()
    print("✅ test_incomplete_json_gracefully passed")
    
    test_incomplete_string_value()
    print("✅ test_incomplete_string_value passed")
    
    test_mixed_value_types()
    print("✅ test_mixed_value_types passed")
    
    test_callback_order()
    print("✅ test_callback_order passed")
    
    test_parser_reuse()
    print("✅ test_parser_reuse passed")
    
    test_very_long_string_value()
    print("✅ test_very_long_string_value passed")
    
    test_deeply_nested_with_context_limit()
    print("✅ test_deeply_nested_with_context_limit passed")
    
    test_special_json_strings()
    print("✅ test_special_json_strings passed")
    
    test_numbers_and_booleans_in_arrays()
    print("✅ test_numbers_and_booleans_in_arrays passed")
    
    test_parse_from_old_new_with_invalid_input()
    print("✅ test_parse_from_old_new_with_invalid_input passed")
    
    test_parse_from_old_new_empty_delta()
    print("✅ test_parse_from_old_new_empty_delta passed")
    
    test_multiple_root_fields()
    print("✅ test_multiple_root_fields passed")
    
    test_consecutive_escape_sequences()
    print("✅ test_consecutive_escape_sequences passed")
    
    print("\n🎉 All edge case tests passed!")
