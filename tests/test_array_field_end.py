"""
Comprehensive tests for array field_end callbacks.
This test suite covers the issue where arrays at the end of JSON objects
don't trigger on_field_end callbacks.
"""

import json
import random
from jaxn import StreamingJSONParser, JSONParserHandler


def test_array_of_strings_at_end():
    """Test that on_field_end is called for array of strings at the end."""
    data = {"name": "John", "tags": ["tag1", "tag2", "tag3"]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have both start and end for 'tags'
    assert ('start', 'tags') in events
    assert ('end', 'tags', ['tag1', 'tag2', 'tag3']) in events


def test_array_of_objects_at_end():
    """Test that on_field_end is called for array of objects at the end."""
    data = {
        "name": "test",
        "items": [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"}
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('array_item', field_name, item))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have both start and end for 'items'
    assert ('start', 'items') in events
    # Should have array_item_end for each object
    assert ('array_item', 'items', {'id': 1, 'name': 'first'}) in events
    assert ('array_item', 'items', {'id': 2, 'name': 'second'}) in events
    # Should have field_end with complete array
    assert ('end', 'items', [{'id': 1, 'name': 'first'}, {'id': 2, 'name': 'second'}]) in events


def test_empty_array_at_end():
    """Test that on_field_end is called for empty array at the end."""
    data = {"name": "test", "items": []}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have both start and end for 'items'
    assert ('start', 'items') in events
    assert ('end', 'items', []) in events


def test_nested_array_at_end():
    """Test that on_field_end is called for nested array at the end of a parent object."""
    data = {
        "sections": [
            {
                "heading": "Section 1",
                "references": [
                    {"title": "Ref 1", "url": "http://example.com/1"},
                    {"title": "Ref 2", "url": "http://example.com/2"}
                ]
            }
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', path, field_name, type(parsed_value).__name__))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'references' array
    references_ends = [e for e in events if e[0] == 'end' and e[2] == 'references']
    assert len(references_ends) == 1
    assert references_ends[0][3] == 'list'  # parsed_value should be a list
    
    # Should also have field_end for 'sections' array
    sections_ends = [e for e in events if e[0] == 'end' and e[2] == 'sections']
    assert len(sections_ends) == 1
    assert sections_ends[0][3] == 'list'


def test_multiple_arrays_at_end():
    """Test that on_field_end is called for multiple consecutive arrays at the end."""
    data = {
        "name": "test",
        "items": [{"id": 1}],
        "tags": ["tag1", "tag2"]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for both arrays
    assert ('end', 'items', [{'id': 1}]) in events
    assert ('end', 'tags', ['tag1', 'tag2']) in events


def test_array_with_streaming():
    """Test that on_field_end is called for arrays when parsing character-by-character."""
    data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Should have field_end for 'users' array
    users_end = [e for e in events if e[1] == 'users']
    assert len(users_end) == 1
    assert users_end[0][2] == [{'name': 'Alice'}, {'name': 'Bob'}]


def test_array_at_end_with_random_chunks():
    """Test array field_end with random chunk sizes simulating API streaming."""
    data = {
        "answer": "Some answer text",
        "confidence": 0.95,
        "followup_questions": [
            "What is question 1?",
            "What is question 2?",
            "What is question 3?"
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse with random chunk sizes
    random.seed(42)
    pos = 0
    while pos < len(json_str):
        chunk_size = random.randint(1, 20)
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
    
    # Should have field_end for 'followup_questions'
    followup_end = [e for e in events if e[0] == 'end' and e[1] == 'followup_questions']
    assert len(followup_end) == 1
    assert followup_end[0][2] == [
        "What is question 1?",
        "What is question 2?",
        "What is question 3?"
    ]


def test_real_world_rag_response():
    """Test the exact scenario from the issue: RAG response with followup_questions array at the end."""
    raw_json = '{"answer":"## Using LLM as a Judge\\n\\nIn this tutorial, you will learn how to evaluate text for custom criteria using an LLM as the judge. The tutorial covers two primary approaches:\\n\\n1. **Reference-based Evaluation**: This method compares new responses against a pre-approved reference. It is useful for regression testing when a \\"ground truth\\" exists.\\n\\n2. **Open-ended Evaluation**: In this approach, responses are assessed based on custom criteria, allowing evaluation when no reference is available.\\n\\n### Steps Covered in the Tutorial\\n- **Create an Evaluation Dataset**: Construct a toy Q&A dataset consisting of questions, approved target responses, new system responses, and their manual labels.\\n- **Design an LLM Evaluator Prompt**: Create and run an LLM evaluator to judge the quality of responses.\\n- **Evaluate the Judge**: Compare the evaluations made by the LLM against manual labels to assess accuracy and quality.\\n\\n### Requirements\\n- Basic knowledge of Python.\\n- An OpenAI API key to utilize the LLM evaluator.\\n\\nThe tutorial will assist you in integrating the LLM evaluator into various workflows, such as prompt testing and response quality assessments.","found_answer":true,"confidence":0.95,"confidence_explanation":"The answer is based on direct information from the provided documentation, which outlines how to use an LLM as a judge for evaluating responses.","answer_type":"how-to","followup_questions":["What are the benefits of using LLM as a judge?","Can I customize the evaluation criteria for the LLM judge?","How do I set up my environment to use LLM as a judge?"]}'
    
    events = []
    
    class RAGResponseHandler(JSONParserHandler):
        def on_field_start(self, path, field_name):
            events.append(('start', path, field_name))
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append(('end', path, field_name))
        
        def on_array_item_end(self, path, field_name, item=None):
            events.append(('array_item_end', path, field_name))
    
    parser = StreamingJSONParser(RAGResponseHandler())
    
    # Parse character by character to simulate streaming
    for c in raw_json:
        parser.parse_incremental(c)
    
    # Verify all fields have both start and end
    fields = ['answer', 'confidence_explanation', 'answer_type', 'followup_questions']
    for field in fields:
        assert ('start', '/', field) in events, f"Missing start event for {field}"
        assert ('end', '/', field) in events, f"Missing end event for {field}"


def test_array_of_numbers_at_end():
    """Test array of numbers at the end."""
    data = {"name": "test", "scores": [1, 2, 3, 4, 5]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'scores'
    assert ('scores', [1, 2, 3, 4, 5]) in events


def test_array_of_booleans_at_end():
    """Test array of booleans at the end."""
    data = {"name": "test", "flags": [True, False, True]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'flags'
    assert ('flags', [True, False, True]) in events


def test_array_with_nulls_at_end():
    """Test array with null values at the end."""
    data = {"name": "test", "values": [1, None, 3]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'values'
    assert ('values', [1, None, 3]) in events


def test_array_with_mixed_types_at_end():
    """Test array with mixed types at the end."""
    data = {"name": "test", "mixed": [1, "two", True, None, {"key": "value"}]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'mixed'
    assert ('mixed', [1, "two", True, None, {"key": "value"}]) in events


def test_nested_arrays_at_end():
    """Test nested arrays (arrays of arrays) at the end."""
    data = {"name": "test", "matrix": [[1, 2], [3, 4], [5, 6]]}
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'matrix' with the complete nested array
    assert ('matrix', [[1, 2], [3, 4], [5, 6]]) in events


def test_deeply_nested_array_at_end():
    """Test deeply nested structure with array at the end."""
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "items": ["a", "b", "c"]
                }
            }
        }
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'items':
                events.append((path, field_name, parsed_value))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'items'
    assert len(events) == 1
    assert events[0][1] == 'items'
    assert events[0][2] == ["a", "b", "c"]
    assert 'level1' in events[0][0]
    assert 'level2' in events[0][0]
    assert 'level3' in events[0][0]


def test_array_field_end_value_string():
    """Test that the value parameter contains the array content without brackets."""
    data = {"tags": ["tag1", "tag2"]}
    json_str = json.dumps(data)
    
    captured_value = [None]
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == 'tags':
                captured_value[0] = value
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # The value should be the array content (without the outer brackets)
    assert captured_value[0] == '"tag1", "tag2"' or captured_value[0] == '"tag1","tag2"'


def test_multiple_nested_arrays_all_get_field_end():
    """Test that all nested arrays get field_end callbacks."""
    data = {
        "sections": [
            {
                "heading": "Section 1",
                "content": "Content 1",
                "references": [
                    {"title": "Ref 1"},
                    {"title": "Ref 2"}
                ]
            },
            {
                "heading": "Section 2",
                "content": "Content 2",
                "references": [
                    {"title": "Ref 3"}
                ]
            }
        ],
        "tags": ["tag1", "tag2"]
    }
    json_str = json.dumps(data)
    
    field_ends = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name in ['sections', 'references', 'tags']:
                field_ends.append((path, field_name, type(parsed_value).__name__))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Should have field_end for 'sections'
    sections_ends = [e for e in field_ends if e[1] == 'sections']
    assert len(sections_ends) == 1
    assert sections_ends[0][2] == 'list'
    
    # Should have field_end for 'references' (twice, once per section)
    references_ends = [e for e in field_ends if e[1] == 'references']
    assert len(references_ends) == 2
    
    # Should have field_end for 'tags'
    tags_ends = [e for e in field_ends if e[1] == 'tags']
    assert len(tags_ends) == 1
    assert tags_ends[0][2] == 'list'


def test_array_at_end_preserves_path_correctly():
    """Test that path is correct when field_end is called for arrays."""
    data = {
        "sections": [
            {
                "items": [1, 2, 3]
            }
        ]
    }
    json_str = json.dumps(data)
    
    events = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            events.append((path, field_name))
    
    parser = StreamingJSONParser(TestHandler())
    parser.parse_incremental(json_str)
    
    # Find the 'items' field_end event
    items_events = [e for e in events if e[1] == 'items']
    assert len(items_events) == 1
    assert items_events[0][0] == '/sections'
    
    # Find the 'sections' field_end event
    sections_events = [e for e in events if e[1] == 'sections']
    assert len(sections_events) == 1
    assert sections_events[0][0] == '/'


if __name__ == "__main__":
    # Run tests manually
    test_array_of_strings_at_end()
    print("✅ test_array_of_strings_at_end passed")
    
    test_array_of_objects_at_end()
    print("✅ test_array_of_objects_at_end passed")
    
    test_empty_array_at_end()
    print("✅ test_empty_array_at_end passed")
    
    test_nested_array_at_end()
    print("✅ test_nested_array_at_end passed")
    
    test_multiple_arrays_at_end()
    print("✅ test_multiple_arrays_at_end passed")
    
    test_array_with_streaming()
    print("✅ test_array_with_streaming passed")
    
    test_array_at_end_with_random_chunks()
    print("✅ test_array_at_end_with_random_chunks passed")
    
    test_real_world_rag_response()
    print("✅ test_real_world_rag_response passed")
    
    test_array_of_numbers_at_end()
    print("✅ test_array_of_numbers_at_end passed")
    
    test_array_of_booleans_at_end()
    print("✅ test_array_of_booleans_at_end passed")
    
    test_array_with_nulls_at_end()
    print("✅ test_array_with_nulls_at_end passed")
    
    test_array_with_mixed_types_at_end()
    print("✅ test_array_with_mixed_types_at_end passed")
    
    test_nested_arrays_at_end()
    print("✅ test_nested_arrays_at_end passed")
    
    test_deeply_nested_array_at_end()
    print("✅ test_deeply_nested_array_at_end passed")
    
    test_array_field_end_value_string()
    print("✅ test_array_field_end_value_string passed")
    
    test_multiple_nested_arrays_all_get_field_end()
    print("✅ test_multiple_nested_arrays_all_get_field_end passed")
    
    test_array_at_end_preserves_path_correctly()
    print("✅ test_array_at_end_preserves_path_correctly passed")
    
    print("\n🎉 All array field_end tests passed!")
