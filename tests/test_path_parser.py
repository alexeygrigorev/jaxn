"""Test the path-based parser functionality."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json


def test_path_tracking():
    """Test that parser correctly tracks paths through nested structures."""
    data = {
        "title": "Main Title",
        "sections": [
            {
                "heading": "Section 1",
                "content": "Content here",
                "references": [
                    {"title": "Ref Title 1", "filename": "ref1.mdx"},
                    {"title": "Ref Title 2", "filename": "ref2.mdx"}
                ]
            }
        ],
        "references": [
            {"title": "Root Ref", "filename": ""}
        ]
    }

    json_str = json.dumps(data)
    
    class PathCollectorHandler(JSONParserHandler):
        def __init__(self):
            self.paths = []
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            self.paths.append((path, field_name, value))
    
    handler = PathCollectorHandler()
    parser = StreamingJSONParser(handler)
    
    for char in json_str:
        parser.parse_incremental(char)
    
    # Verify we collected paths
    assert len(handler.paths) > 0
    
    # Check root-level title
    root_title = [p for p in handler.paths if p[0] == '/' and p[1] == 'title']
    assert len(root_title) == 1
    assert root_title[0][2] == "Main Title"
    
    # Check section references (should have path containing 'sections' and 'references')
    section_refs = [p for p in handler.paths if 'sections' in p[0] and 'references' in p[0] and p[1] == 'title']
    assert len(section_refs) == 2
    assert section_refs[0][2] == "Ref Title 1"
    assert section_refs[1][2] == "Ref Title 2"
    
    # Check root references
    root_refs = [p for p in handler.paths if p[0] == '/references' and p[1] == 'title']
    assert len(root_refs) == 1
    assert root_refs[0][2] == "Root Ref"
