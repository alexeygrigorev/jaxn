"""Test array item start/end callbacks."""

from streaming_json_parser import StreamingJSONParser, JSONParserHandler
import json


def test_array_item_callbacks():
    """Test that parser fires callbacks when array items start and end."""
    data = {
        "items": [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"}
        ]
    }
    
    json_str = json.dumps(data)
    
    class ArrayTracker(JSONParserHandler):
        def __init__(self):
            self.starts = []
            self.ends = []
        
        def on_array_item_start(self, path, field_name):
            self.starts.append((path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            self.ends.append((path, field_name))
    
    handler = ArrayTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have 2 starts and 2 ends for the two objects in the array
    assert len(handler.starts) == 2
    assert len(handler.ends) == 2
    
    # All should be for 'items' field at root path
    assert all(path == '' and field == 'items' for path, field in handler.starts)
    assert all(path == '' and field == 'items' for path, field in handler.ends)


def test_nested_array_callbacks():
    """Test array callbacks with nested structure."""
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
    
    class NestedArrayTracker(JSONParserHandler):
        def __init__(self):
            self.events = []
        
        def on_array_item_start(self, path, field_name):
            self.events.append(('start', path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            self.events.append(('end', path, field_name))
    
    handler = NestedArrayTracker()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have events for sections array (1 object) and references array (2 objects)
    starts = [e for e in handler.events if e[0] == 'start']
    ends = [e for e in handler.events if e[0] == 'end']
    
    assert len(starts) == 3  # 1 section + 2 references
    assert len(ends) == 3
    
    # Check sections events
    section_starts = [e for e in starts if e[2] == 'sections']
    assert len(section_starts) == 1
    assert section_starts[0][1] == ''  # root path
    
    # Check references events
    ref_starts = [e for e in starts if e[2] == 'references']
    assert len(ref_starts) == 2
    assert all(e[1] == '/sections' for e in ref_starts)


def test_array_callbacks_with_streaming():
    """Test array callbacks work with character-by-character streaming."""
    data = {
        "users": [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
    }
    
    json_str = json.dumps(data)
    
    class StreamingArrayTracker(JSONParserHandler):
        def __init__(self):
            self.item_count = 0
        
        def on_array_item_start(self, path, field_name):
            pass
        
        def on_array_item_end(self, path, field_name, item=None):
            if field_name == 'users':
                self.item_count += 1
    
    handler = StreamingArrayTracker()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert handler.item_count == 2


def test_reference_collection_pattern():
    """Test the pattern used in streamed_user_profile.py for collecting references."""
    data = {
        "title": "Main Title",
        "sections": [
            {
                "heading": "Section 1",
                "content": "Some content",
                "references": [
                    {"title": "Ref 1", "filename": "ref1.mdx"},
                    {"title": "Ref 2", "filename": "ref2.mdx"}
                ]
            }
        ],
        "references": [
            {"title": "Root Ref", "filename": "root.mdx"}
        ]
    }
    
    json_str = json.dumps(data)
    
    class ReferenceCollector(JSONParserHandler):
        def __init__(self):
            self.current_ref = {}
            self.collected_refs = []
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'title' and 'references' in path:
                self.current_ref['title'] = value
            elif field_name == 'filename' and 'references' in path:
                self.current_ref['filename'] = value
        
        def on_array_item_end(self, path, field_name, item=None):
            if field_name == 'references' and self.current_ref:
                self.collected_refs.append(self.current_ref.copy())
                self.current_ref = {}
    
    handler = ReferenceCollector()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have collected 3 references total
    assert len(handler.collected_refs) == 3
    
    # Check section references
    section_refs = [r for r in handler.collected_refs if 'ref1.mdx' in r.get('filename', '') or 'ref2.mdx' in r.get('filename', '')]
    assert len(section_refs) == 2
    
    # Check root reference
    root_refs = [r for r in handler.collected_refs if 'root.mdx' in r.get('filename', '')]
    assert len(root_refs) == 1
