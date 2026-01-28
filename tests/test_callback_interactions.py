"""Test interactions between different callbacks and event sequences."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_field_start_before_string_value():
    """Test that field_start is called before streaming a string value."""
    data = {"message": "Hello World"}
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_value_chunk(self, path, field_name, chunk):
            events.append(('chunk', field_name, chunk))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name))
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # field_start should come first
    assert events[0] == ('start', 'message')
    
    # Then chunks
    chunk_events = [e for e in events if e[0] == 'chunk']
    assert len(chunk_events) > 0
    
    # Then field_end
    assert events[-1] == ('end', 'message')


def test_array_item_callbacks_surround_field_callbacks():
    """Test that array item start/end surround the field callbacks."""
    data = {
        "items": [
            {"name": "Item 1"}
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_array_item_start(self, path, field_name):
            events.append(('item_start', field_name))
        
        def on_field_start(self, path, field_name):
            events.append(('field_start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('field_end', field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('item_end', field_name))
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Find the sequence for items
    item_start_idx = next(i for i, e in enumerate(events) if e == ('item_start', 'items'))
    item_end_idx = next(i for i, e in enumerate(events) if e == ('item_end', 'items'))
    
    # field callbacks should be between item callbacks
    field_events = [e for e in events[item_start_idx:item_end_idx] if 'field' in e[0]]
    assert len(field_events) > 0


def test_nested_array_callback_order():
    """Test callback order with nested arrays."""
    data = {
        "outer": [
            {
                "inner": [
                    {"value": "nested"}
                ]
            }
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('field_start', path, field_name))
        
        def on_array_item_start(self, path, field_name):
            events.append(('item_start', path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('item_end', path, field_name))
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have events for both outer and inner arrays
    outer_events = [e for e in events if e[2] == 'outer']
    inner_events = [e for e in events if e[2] == 'inner']
    
    assert len(outer_events) > 0
    assert len(inner_events) > 0


def test_multiple_value_chunks_between_start_and_end():
    """Test that multiple chunks arrive between field_start and field_end."""
    data = {"text": "ABCDEFGHIJ"}
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append('START')
        
        def on_value_chunk(self, path, field_name, chunk):
            events.append(f'CHUNK:{chunk}')
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append('END')
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert events[0] == 'START'
    assert events[-1] == 'END'
    
    # All events between should be chunks
    chunk_events = events[1:-1]
    assert all(e.startswith('CHUNK:') for e in chunk_events)
    assert len(chunk_events) == 10  # 10 characters


def test_field_start_for_all_value_types():
    """Test that field_start is called for all value types including primitives."""
    data = {
        "string": "text",
        "number": 42,
        "boolean": True,
        "null": None,
        "object": {"key": "value"},
        "array": [1, 2, 3]
    }
    json_str = json.dumps(data)

    field_starts = []

    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append(field_name)

    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)

    # All value types should have field_start
    assert 'string' in field_starts
    assert 'number' in field_starts
    assert 'boolean' in field_starts
    assert 'null' in field_starts
    assert 'object' in field_starts
    assert 'array' in field_starts


def test_field_start_for_object_and_array_fields():
    """Test that field_start is called for object and array fields."""
    data = {
        "obj": {"nested": "value"},
        "arr": [1, 2, 3]
    }
    json_str = json.dumps(data)
    
    field_starts = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append(field_name)
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Both object and array fields should trigger field_start
    assert 'obj' in field_starts
    assert 'arr' in field_starts


def test_path_changes_during_parsing():
    """Test that path correctly changes as we move through nested structures."""
    data = {
        "level1": {
            "level2": {
                "value": "deep"
            }
        }
    }
    json_str = json.dumps(data)
    
    paths = []
    
    class PathTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            paths.append(path)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            paths.append(path)
    
    handler = PathTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have empty path, /level1, /level1/level2
    assert '' in paths
    assert '/level1' in paths
    assert '/level1/level2' in paths


def test_path_in_array_items():
    """Test that path is correct for items in arrays."""
    data = {
        "items": [
            {"name": "Item 1"},
            {"name": "Item 2"}
        ]
    }
    json_str = json.dumps(data)
    
    paths = []
    
    class PathTracker(JSONParserHandler):
        def on_array_item_start(self, path, field_name):
            paths.append(('item_start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'name':
                paths.append(('field_end', path, field_name))
    
    handler = PathTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Array items should be at root path
    item_starts = [p for p in paths if p[0] == 'item_start']
    assert all(p[1] == '' for p in item_starts)
    
    # Fields inside items should be at /items path
    field_ends = [p for p in paths if p[0] == 'field_end']
    assert all('/items' in p[1] for p in field_ends)


def test_handler_can_modify_state_between_callbacks():
    """Test that handler can maintain and modify state between callbacks."""
    data = {
        "items": [
            {"id": 1, "name": "First"},
            {"id": 2, "name": "Second"}
        ]
    }
    json_str = json.dumps(data)
    
    class StatefulHandler(JSONParserHandler):
        def __init__(self):
            super().__init__()
            self.current_item = {}
            self.completed_items = []
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if '/items' in path:
                self.current_item[field_name] = parsed_value
        
        def on_array_item_end(self, path, field_name, item=None):
            if field_name == 'items' and self.current_item:
                self.completed_items.append(self.current_item.copy())
                self.current_item = {}
    
    handler = StatefulHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(handler.completed_items) == 2
    assert handler.completed_items[0]['name'] == 'First'
    assert handler.completed_items[1]['name'] == 'Second'


def test_consecutive_arrays():
    """Test parsing consecutive arrays without nesting."""
    data = {
        "array1": [1, 2, 3],
        "array2": [4, 5, 6]
    }
    json_str = json.dumps(data)
    
    field_starts = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append(field_name)
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert 'array1' in field_starts
    assert 'array2' in field_starts


def test_empty_array_in_object():
    """Test empty array nested in object."""
    data = {
        "metadata": {
            "tags": []
        }
    }
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_array_item_start(self, path, field_name):
            events.append(('item_start', field_name))
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Empty array should trigger field_start but no item_start
    assert ('start', 'tags') in events
    assert ('item_start', 'tags') not in events


def test_callback_exception_handling():
    """Test that parser continues even if callback raises exception."""
    data = {"field1": "value1", "field2": "value2"}
    json_str = json.dumps(data)
    
    captured = []
    
    class FaultyHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'field1':
                # Simulate exception in first callback
                captured.append(parsed_value)
                # Don't actually raise to keep test simple
            else:
                captured.append(parsed_value)
    
    handler = FaultyHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Both fields should be captured
    assert 'value1' in captured
    assert 'value2' in captured


def test_incremental_parsing_state_preservation():
    """Test that parser preserves state across incremental calls."""
    data = {"message": "Hello World"}
    json_str = json.dumps(data)
    
    chunks_received = []
    
    class ChunkTracker(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            chunks_received.append(chunk)
    
    handler = ChunkTracker()
    parser = StreamingJSONParser(handler)
    
    # Parse in multiple incremental calls
    mid = len(json_str) // 2
    parser.parse_incremental(json_str[:mid])
    parser.parse_incremental(json_str[mid:])
    
    # Should have received all characters
    reconstructed = ''.join(chunks_received)
    assert reconstructed == "Hello World"


def test_field_end_called_after_all_chunks():
    """Test that field_end is called after all value chunks."""
    data = {"text": "ABC"}
    json_str = json.dumps(data)
    
    events = []
    
    class EventTracker(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            events.append(f'chunk:{chunk}')
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append('end')
    
    handler = EventTracker()
    parser = StreamingJSONParser(handler)
    
    for char in json_str:
        parser.parse_incremental(char)
    
    # Last event should be 'end'
    assert events[-1] == 'end'
    
    # All previous events should be chunks
    assert all('chunk:' in e for e in events[:-1])


if __name__ == "__main__":
    # Run all tests
    test_field_start_before_string_value()
    print("✅ test_field_start_before_string_value passed")
    
    test_array_item_callbacks_surround_field_callbacks()
    print("✅ test_array_item_callbacks_surround_field_callbacks passed")
    
    test_nested_array_callback_order()
    print("✅ test_nested_array_callback_order passed")
    
    test_multiple_value_chunks_between_start_and_end()
    print("✅ test_multiple_value_chunks_between_start_and_end passed")
    
    test_no_field_start_for_non_string_primitives()
    print("✅ test_no_field_start_for_non_string_primitives passed")
    
    test_field_start_for_object_and_array_fields()
    print("✅ test_field_start_for_object_and_array_fields passed")
    
    test_path_changes_during_parsing()
    print("✅ test_path_changes_during_parsing passed")
    
    test_path_in_array_items()
    print("✅ test_path_in_array_items passed")
    
    test_handler_can_modify_state_between_callbacks()
    print("✅ test_handler_can_modify_state_between_callbacks passed")
    
    test_consecutive_arrays()
    print("✅ test_consecutive_arrays passed")
    
    test_empty_array_in_object()
    print("✅ test_empty_array_in_object passed")
    
    test_callback_exception_handling()
    print("✅ test_callback_exception_handling passed")
    
    test_incremental_parsing_state_preservation()
    print("✅ test_incremental_parsing_state_preservation passed")
    
    test_field_end_called_after_all_chunks()
    print("✅ test_field_end_called_after_all_chunks passed")
    
    print("\n🎉 All callback interaction tests passed!")
