r"""Test unicode escape sequence handling (\uXXXX format)."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_unicode_escape_right_single_quote():
    """Test that \u2019 (right single quotation mark) is properly decoded."""
    # JSON with unicode escape for right single quotation mark (')
    json_str = '{"content": "Here\\u2019s how it works"}'
    
    # Expected result (what standard json.loads produces)
    expected = json.loads(json_str)["content"]
    # \u2019 is the right single quotation mark character
    assert '\u2019' in expected  # Verify we have the unicode character
    
    class TestHandler(JSONParserHandler):
        def __init__(self):
            self.chunks = []
            self.final_value = None
        
        def on_value_chunk(self, path, field_name, chunk):
            self.chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            self.final_value = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Check streaming output
    streamed = ''.join(handler.chunks)
    assert streamed == expected, f"Streamed: {repr(streamed)}, Expected: {repr(expected)}"
    
    # Check final parsed value
    assert handler.final_value == expected, f"Final: {repr(handler.final_value)}, Expected: {repr(expected)}"


def test_unicode_escape_multiple_chars():
    """Test multiple unicode escape sequences in one string."""
    json_str = '{"text": "Hello\\u0020World\\u0021\\u0020Test\\u2019s"}'
    
    # \u0020 = space, \u0021 = !, \u2019 = '
    expected = json.loads(json_str)["text"]
    # Verify it contains the expected characters
    assert ' ' in expected  # space
    assert '!' in expected  # exclamation
    assert '\u2019' in expected  # right single quotation mark
    
    class TestHandler(JSONParserHandler):
        def __init__(self):
            self.chunks = []
            self.final_value = None
        
        def on_value_chunk(self, path, field_name, chunk):
            self.chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            self.final_value = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    streamed = ''.join(handler.chunks)
    assert streamed == expected
    assert handler.final_value == expected


def test_unicode_escape_mixed_with_regular_escapes():
    """Test unicode escapes mixed with regular escape sequences."""
    json_str = '{"text": "Line1\\nLine2\\u2019s\\ttab"}'
    
    expected = json.loads(json_str)["text"]
    # Verify it has the expected characters
    assert '\n' in expected  # newline
    assert '\t' in expected  # tab
    assert '\u2019' in expected  # right single quotation mark
    
    class TestHandler(JSONParserHandler):
        def __init__(self):
            self.chunks = []
            self.final_value = None
        
        def on_value_chunk(self, path, field_name, chunk):
            self.chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            self.final_value = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    streamed = ''.join(handler.chunks)
    assert streamed == expected
    assert handler.final_value == expected


def test_unicode_escape_in_nested_structure():
    """Test unicode escapes in a nested JSON structure like the issue example."""
    data = {
        "found_answer": True,
        "sections": [
            {
                "content": "Here\u2019s how it works:\n1. Setup\n2. Running"  # Using actual unicode char
            }
        ]
    }
    
    # When dumped to JSON, some unicode chars might be escaped
    json_str = json.dumps(data)
    
    # Now replace the unicode char with escape sequence
    json_str_unicode = json_str.replace('\u2019', '\\u2019')
    
    expected_content = "Here\u2019s how it works:\n1. Setup\n2. Running"
    
    class TestHandler(JSONParserHandler):
        def __init__(self):
            self.content_chunks = []
            self.content_value = None
        
        def on_value_chunk(self, path, field_name, chunk):
            if field_name == 'content':
                self.content_chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'content':
                self.content_value = parsed_value
    
    handler = TestHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str_unicode)
    
    streamed = ''.join(handler.content_chunks)
    assert streamed == expected_content
    assert handler.content_value == expected_content
