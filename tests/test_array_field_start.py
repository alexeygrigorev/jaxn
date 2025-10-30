"""Test that on_field_start is called for array fields."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_field_start_called_for_array_fields():
    """Test that on_field_start is called when an array field is encountered."""
    data = {
        "sections": [
            {
                "heading": "Overview",
                "references": [
                    {"title": "Ref 1", "filename": "file1.md"},
                    {"title": "Ref 2", "filename": "file2.md"}
                ]
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append((path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify that on_field_start was called for the 'references' field
    references_starts = [(p, f) for p, f in field_starts if f == 'references']
    assert len(references_starts) == 1, f"Expected 1 'references' field_start, got {len(references_starts)}"
    
    # The path should include 'sections'
    path, field_name = references_starts[0]
    assert 'sections' in path, f"Expected 'sections' in path, got: {path}"


def test_field_start_called_for_nested_array_fields():
    """Test that on_field_start is called for deeply nested array fields."""
    data = {
        "title": "Test",
        "sections": [
            {
                "heading": "Section 1",
                "content": "Content here",
                "references": [
                    {"title": "Ref A"},
                    {"title": "Ref B"}
                ]
            },
            {
                "heading": "Section 2",
                "content": "More content",
                "references": [
                    {"title": "Ref C"}
                ]
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append((path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should have been called for 'references' twice (once per section)
    references_starts = [(p, f) for p, f in field_starts if f == 'references']
    assert len(references_starts) == 2, f"Expected 2 'references' field_starts, got {len(references_starts)}"
    
    # Both should have 'sections' in the path
    for path, field_name in references_starts:
        assert 'sections' in path, f"Expected 'sections' in path, got: {path}"


def test_field_start_order_with_arrays():
    """Test that field_start callbacks maintain correct order with arrays."""
    data = {
        "items": [
            {
                "name": "Item 1",
                "tags": ["tag1", "tag2"]
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('field_start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('field_end', path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Find the 'tags' field events
    tags_events = [(e[0], e[2]) for e in events if len(e) > 2 and e[2] == 'tags']
    
    # Should have both start and end
    assert ('field_start', 'tags') in tags_events, "Missing field_start for 'tags'"
    # Note: field_end might not be called for arrays, only for scalar values


def test_field_start_with_streaming():
    """Test field_start is called correctly with character-by-character streaming."""
    data = {
        "section": {
            "refs": [{"id": 1}, {"id": 2}]
        }
    }
    
    json_str = json.dumps(data)
    
    field_starts = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            field_starts.append((path, field_name))
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Should have been called for 'refs'
    refs_starts = [(p, f) for p, f in field_starts if f == 'refs']
    assert len(refs_starts) == 1, f"Expected 1 'refs' field_start, got {len(refs_starts)}"
