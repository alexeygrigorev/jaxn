"""Test parsed values in callbacks."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_parsed_value_in_field_end():
    """Test that parsed_value is provided in on_field_end for string values."""
    data = {"name": "Alice", "age": "30"}
    json_str = json.dumps(data)
    
    parsed_values = {}
    raw_values = {}
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            raw_values[field_name] = value
            parsed_values[field_name] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # For string values, parsed_value should equal the string value
    assert parsed_values['name'] == 'Alice'
    assert parsed_values['age'] == '30'
    
    # And should match the raw value
    assert parsed_values['name'] == raw_values['name']
    assert parsed_values['age'] == raw_values['age']


def test_parsed_value_with_escape_sequences():
    """Test that parsed_value correctly captures strings with escape sequences."""
    data = {"message": "Line 1\nLine 2\tTabbed"}
    json_str = json.dumps(data)  # This will escape the newline and tab
    
    captured = {}
    value_chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            value_chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            captured['raw'] = value
            captured['parsed'] = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # The raw value contains escape sequences as they appear in JSON
    assert captured['raw'] == 'Line 1\\nLine 2\\tTabbed'
    
    # The parsed_value should be the decoded string (actual newline and tab)
    assert captured['parsed'] == 'Line 1\nLine 2\tTabbed'
    
    # on_value_chunk should have received the decoded characters
    reconstructed = ''.join(value_chunks)
    assert reconstructed == "Line 1\nLine 2\tTabbed"  # Actual newline and tab characters
    
    # The parsed value should match what we reconstructed from chunks
    assert captured['parsed'] == reconstructed
    
    # Verify we can decode the buffer value to get the actual string
    assert json.loads(f'"{captured["raw"]}"') == reconstructed


def test_parsed_value_consistency_across_chunks():
    """Test that parsed_value is consistent regardless of chunk sizes."""
    data = {
        "title": "Test Title",
        "description": "A longer description with multiple words",
        "code": "function() { return 42; }"
    }
    json_str = json.dumps(data)
    
    # Parse all at once
    parsed_all_at_once = {}
    
    class TestHandler1(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            parsed_all_at_once[field_name] = parsed_value
    
    handler1 = TestHandler1()
    parser1 = StreamingJSONParser(handler1)
    parser1.parse_incremental(json_str)
    
    # Parse character by character
    parsed_char_by_char = {}
    
    class TestHandler2(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            parsed_char_by_char[field_name] = parsed_value
    
    handler2 = TestHandler2()
    parser2 = StreamingJSONParser(handler2)
    
    for char in json_str:
        parser2.parse_incremental(char)
    
    # Both should produce identical parsed values
    assert parsed_all_at_once == parsed_char_by_char
    assert parsed_all_at_once['title'] == "Test Title"
    assert parsed_all_at_once['description'] == "A longer description with multiple words"
    assert parsed_all_at_once['code'] == "function() { return 42; }"


def test_parsed_dict_in_array_item_end():
    """Test that complete dict is provided when array item ends."""
    data = {
        "users": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                collected_items.append(item.copy())
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have collected both user objects
    assert len(collected_items) == 2
    assert collected_items[0] == {"name": "Alice", "age": 30}
    assert collected_items[1] == {"name": "Bob", "age": 25}


def test_nested_array_parsed_dicts():
    """Test parsed dicts with nested arrays."""
    data = {
        "sections": [
            {
                "heading": "Section 1",
                "references": [
                    {"title": "Ref 1", "filename": "ref1.mdx"},
                    {"title": "Ref 2", "filename": "ref2.mdx"}
                ]
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    section_items = []
    reference_items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'sections':
                    section_items.append(item.copy())
                elif field_name == 'references':
                    reference_items.append(item.copy())
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have 1 section
    assert len(section_items) == 1
    assert section_items[0]['heading'] == "Section 1"
    
    # Should have 2 references
    assert len(reference_items) == 2
    assert reference_items[0] == {"title": "Ref 1", "filename": "ref1.mdx"}
    assert reference_items[1] == {"title": "Ref 2", "filename": "ref2.mdx"}


def test_streaming_with_parsed_values():
    """Test that parsed values work with character-by-character streaming."""
    data = {
        "items": [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "inactive"}
        ]
    }
    
    json_str = json.dumps(data)
    
    parsed_items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'items':
                parsed_items.append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert len(parsed_items) == 2
    assert parsed_items[0]['id'] == 1
    assert parsed_items[0]['status'] == "active"
    assert parsed_items[1]['id'] == 2
    assert parsed_items[1]['status'] == "inactive"


def test_item_parameter_completeness():
    """Test that item parameter contains complete, valid parsed dictionaries."""
    data = {
        "users": [
            {
                "name": "Alice",
                "email": "alice@example.com",
                "age": 30,
                "active": True,
                "metadata": {"role": "admin", "level": 5}
            },
            {
                "name": "Bob",
                "email": "bob@example.com",
                "age": 25,
                "active": False,
                "metadata": {"role": "user", "level": 1}
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_items = []
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'users':
                collected_items.append(item.copy())
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify we got both items
    assert len(collected_items) == 2
    
    # Verify first item is complete
    alice = collected_items[0]
    assert isinstance(alice, dict)
    assert alice['name'] == "Alice"
    assert alice['email'] == "alice@example.com"
    assert alice['age'] == 30
    assert alice['active'] is True
    assert isinstance(alice['metadata'], dict)
    assert alice['metadata']['role'] == "admin"
    assert alice['metadata']['level'] == 5
    
    # Verify second item is complete
    bob = collected_items[1]
    assert isinstance(bob, dict)
    assert bob['name'] == "Bob"
    assert bob['email'] == "bob@example.com"
    assert bob['age'] == 25
    assert bob['active'] is False
    assert isinstance(bob['metadata'], dict)
    assert bob['metadata']['role'] == "user"
    assert bob['metadata']['level'] == 1


def test_item_with_nested_arrays():
    """Test that item contains properly parsed nested arrays."""
    data = {
        "products": [
            {
                "name": "Laptop",
                "tags": ["electronics", "computers", "portable"],
                "specs": {
                    "dimensions": [15.6, 10.5, 0.8],
                    "ports": ["USB-C", "HDMI", "Audio"]
                }
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_item = None
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            nonlocal collected_item
            if item and field_name == 'products':
                collected_item = item
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify the item was parsed correctly
    assert collected_item is not None
    assert collected_item['name'] == "Laptop"
    
    # Verify nested array
    assert isinstance(collected_item['tags'], list)
    assert collected_item['tags'] == ["electronics", "computers", "portable"]
    
    # Verify nested object with arrays
    assert isinstance(collected_item['specs'], dict)
    assert isinstance(collected_item['specs']['dimensions'], list)
    assert collected_item['specs']['dimensions'] == [15.6, 10.5, 0.8]
    assert isinstance(collected_item['specs']['ports'], list)
    assert collected_item['specs']['ports'] == ["USB-C", "HDMI", "Audio"]


def test_item_parameter_none_handling():
    """Test that item parameter gracefully handles parsing failures."""
    # Create invalid JSON structure that might fail parsing
    # But our parser should still call the callback, possibly with None
    data = {
        "items": [
            {"id": 1, "name": "Valid"},
            {"id": 2, "name": "Also Valid"}
        ]
    }
    
    json_str = json.dumps(data)
    
    callback_count = 0
    items_with_data = 0
    
    class TestHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            nonlocal callback_count, items_with_data
            if field_name == 'items':
                callback_count += 1
                if item is not None:
                    items_with_data += 1
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have been called for each item
    assert callback_count == 2
    # All should have valid data
    assert items_with_data == 2


def test_parsed_value_vs_item_consistency():
    """Test that parsed_value for fields and item for arrays are consistent."""
    data = {
        "metadata": {
            "version": "1.0",
            "timestamp": "2024-01-01"
        },
        "records": [
            {"id": 1, "value": "test"},
            {"id": 2, "value": "data"}
        ]
    }
    
    json_str = json.dumps(data)
    
    field_values = {}
    array_items = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if parsed_value is not None:
                field_values[field_name] = parsed_value
        
        def on_array_item_end(self, path, field_name, item=None):
            if item is not None:
                array_items.append(item)
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify field values were captured
    assert 'version' in field_values
    assert field_values['version'] == "1.0"
    assert 'timestamp' in field_values
    assert field_values['timestamp'] == "2024-01-01"
    
    # Verify array items were captured
    assert len(array_items) == 2
    assert array_items[0] == {"id": 1, "value": "test"}
    assert array_items[1] == {"id": 2, "value": "data"}
    
    # Verify the items contain the field values
    for item in array_items:
        assert 'id' in item
        assert 'value' in item
        assert isinstance(item['id'], int)
        assert isinstance(item['value'], str)
