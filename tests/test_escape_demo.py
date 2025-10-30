"""Test escape sequence handling in streaming mode."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_escape_sequences_in_streaming():
    """Test that escape sequences are properly decoded when streaming character by character."""
    data = {
        "title": "Test Title",
        "sections": [
            {
                "heading": "Section 1",
                "content": "Line 1\nLine 2\n\nLine 3 with\ttab"
            }
        ]
    }

    json_str = json.dumps(data)
    
    class StreamCollectorHandler(JSONParserHandler):
        def __init__(self):
            self.chunks = []
        
        def on_value_chunk(self, path, field_name, chunk):
            if field_name == 'content' and 'sections' in path:
                self.chunks.append(chunk)
    
    handler = StreamCollectorHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character to simulate real streaming
    for char in json_str:
        parser.parse_incremental(char)
    
    # Reconstruct the streamed content
    streamed_content = ''.join(handler.chunks)
    
    # Verify that escape sequences were properly decoded during streaming
    assert 'Line 1\nLine 2\n\nLine 3 with\ttab' == streamed_content
    assert '\\n' not in streamed_content  # Should not contain escaped newlines
    assert '\\t' not in streamed_content  # Should not contain escaped tabs
    assert '\n' in streamed_content  # Should contain actual newlines
    assert '\t' in streamed_content  # Should contain actual tabs


def test_multiple_escape_types():
    """Test handling of multiple escape sequence types."""
    data = {
        "text": 'Quote: " Backslash: \\ Tab: \t Newline: \n Slash: /'
    }
    
    json_str = json.dumps(data)
    
    class ChunkCollectorHandler(JSONParserHandler):
        def __init__(self):
            self.chunks = []
        
        def on_value_chunk(self, path, field_name, chunk):
            self.chunks.append(chunk)
    
    handler = ChunkCollectorHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    result = ''.join(handler.chunks)
    
    # All escape sequences should be decoded
    assert '"' in result  # Quote decoded
    assert '\\' in result  # Backslash decoded (but not the escape backslash)
    assert '\t' in result  # Tab decoded
    assert '\n' in result  # Newline decoded
    assert '/' in result  # Forward slash decoded
