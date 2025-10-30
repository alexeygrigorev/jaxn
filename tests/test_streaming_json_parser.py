"""
Tests for the StreamingJSONParser.

The parser uses a handler pattern similar to SAX parsers for XML.
Instead of individual callback functions, you implement a JSONParserHandler class
with methods for the events you care about:
- on_field_start(context, field_name): Called when entering a field value
- on_field_end(context, field_name, value): Called when field value is complete  
- on_value_chunk(context, field_name, chunk): Called for each character in streaming values

This makes it easier to maintain state and organize parsing logic.
"""

import json
import random
from jaxn import StreamingJSONParser, JSONParserHandler


def test_simple_json():
    """Test parsing a simple JSON object."""
    data = {"name": "John", "age": "30"}
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, context, field_name, value, parsed_value=None):
            captured_fields.append((field_name, value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert ("name", "John") in captured_fields
    assert ("age", "30") in captured_fields


def test_nested_json():
    """Test parsing nested JSON with sections."""
    data = {
        "title": "Main Title",
        "sections": [
            {
                "heading": "Section 1",
                "content": "Content 1"
            },
            {
                "heading": "Section 2",
                "content": "Content 2"
            }
        ]
    }
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, context, field_name, value, parsed_value=None):
            captured_fields.append((field_name, value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert ("title", "Main Title") in captured_fields
    assert ("heading", "Section 1") in captured_fields
    assert ("content", "Content 1") in captured_fields
    assert ("heading", "Section 2") in captured_fields
    assert ("content", "Content 2") in captured_fields


def test_random_chunk_sizes():
    """Test parsing with random chunk sizes to simulate API streaming."""
    data = {
        "found_answer": True,
        "title": "Monitoring Data Drift in Production",
        "sections": [
            {
                "heading": "Overview",
                "content": "Data drift monitoring is essential for ML models.",
                "references": []
            },
            {
                "heading": "Implementation",
                "content": "Use Evidently library for drift detection.",
                "references": []
            }
        ],
        "references": []
    }
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, context, field_name, value, parsed_value=None):
            captured_fields.append((field_name, value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse with random chunk sizes
    pos = 0
    while pos < len(json_str):
        chunk_size = random.randint(1, 20)
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
    
    # Verify all expected fields are captured
    assert ("title", "Monitoring Data Drift in Production") in captured_fields
    assert ("heading", "Overview") in captured_fields
    assert ("content", "Data drift monitoring is essential for ML models.") in captured_fields
    assert ("heading", "Implementation") in captured_fields
    assert ("content", "Use Evidently library for drift detection.") in captured_fields


def test_streaming_content():
    """Test that on_value_chunk is called for each character in content."""
    data = {"message": "Hello"}
    json_str = json.dumps(data)
    
    chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, context, field_name, chunk):
            if field_name == "message":
                chunks.append(chunk)
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Should have captured each character of "Hello"
    assert "".join(chunks) == "Hello"


def test_escaped_characters():
    """Test parsing JSON with escaped characters - buffer should keep raw escapes."""
    data = {"text": "Line 1\nLine 2\t\"Quoted\""}
    json_str = json.dumps(data)
    
    captured_value = [None]  # Use list to avoid nonlocal
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            if field_name == "text":
                captured_value[0] = value
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # The parser captures the escaped string as-is from the JSON (with escapes)
    # json.dumps turns \n into \\n, \t into \\t, \" into \\"
    assert captured_value[0] == "Line 1\\nLine 2\\t\\\"Quoted\\\""


def test_escape_sequence_streaming():
    """Test that escape sequences are decoded in on_value_chunk for streaming."""
    data = {"message": "Hello\nWorld\t!"}
    json_str = json.dumps(data)
    
    streamed_chunks = []
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            if field_name == "message":
                streamed_chunks.append(chunk)
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Reconstruct the streamed string
    streamed_text = "".join(streamed_chunks)
    
    # The streamed text should have decoded escape sequences
    assert streamed_text == "Hello\nWorld\t!", f"Expected 'Hello\\nWorld\\t!' but got {repr(streamed_text)}"
    # Verify we actually got a newline character
    assert '\n' in streamed_text
    assert '\t' in streamed_text


def test_escape_sequence_types():
    """Test various escape sequence types."""
    streamed_chunks = []
    final_value = [None]
    
    class TestHandler(JSONParserHandler):
        def on_value_chunk(self, path, field_name, chunk):
            streamed_chunks.append(chunk)
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            final_value[0] = value
    
    # Create JSON with actual escape sequences
    json_str = '{"text": "Line\\nTab\\tQuote\\"Backslash\\\\Slash\\/"}'
    
    parser = StreamingJSONParser(TestHandler())
    for char in json_str:
        parser.parse_incremental(char)
    
    # Check streamed output has decoded escapes
    streamed_text = "".join(streamed_chunks)
    assert '\n' in streamed_text, "Should contain actual newline"
    assert '\t' in streamed_text, "Should contain actual tab"
    assert '"' in streamed_text, "Should contain actual quote"
    assert '\\' in streamed_text, "Should contain actual backslash"
    
    # Buffer keeps raw escapes
    assert final_value[0] == "Line\\nTab\\tQuote\\\"Backslash\\\\Slash\\/"


def test_context_detection():
    """Test that path helps distinguish between root and nested fields."""
    data = {
        "title": "Root Title",
        "sections": [
            {
                "title": "Nested Title",
                "content": "Some content"
            }
        ]
    }
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, path, field_name, value, parsed_value=None):
            # Check if we're in sections based on path
            in_sections = 'sections' in path
            captured_fields.append((field_name, value, in_sections, path))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Find the title fields
    titles = [(name, val, in_sec, path) for name, val, in_sec, path in captured_fields if name == "title"]
    
    # Should have two titles, one not in sections, one in sections
    assert len(titles) == 2
    root_titles = [t for t in titles if not t[2]]
    nested_titles = [t for t in titles if t[2]]
    
    assert len(root_titles) == 1
    assert root_titles[0][1] == "Root Title"
    assert root_titles[0][3] == ""  # Root path is empty
    assert len(nested_titles) == 1
    assert nested_titles[0][1] == "Nested Title"
    assert nested_titles[0][3] == "/sections"  # Nested in sections


def test_parse_from_old_new():
    """Test the convenience method parse_from_old_new."""
    data = {"name": "Alice", "city": "NYC"}
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, context, field_name, value, parsed_value=None):
            captured_fields.append((field_name, value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Simulate incremental text growth
    previous = ""
    for i in range(1, len(json_str) + 1):
        current = json_str[:i]
        parser.parse_from_old_new(previous, current)
        previous = current
    
    assert ("name", "Alice") in captured_fields
    assert ("city", "NYC") in captured_fields


def test_field_start_callback():
    """Test that on_field_start is called when entering a field value."""
    data = {"status": "active", "count": "42"}
    json_str = json.dumps(data)
    
    started_fields = []
    ended_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_start(self, context, field_name):
            started_fields.append(field_name)
        
        def on_field_end(self, context, field_name, value, parsed_value=None):
            ended_fields.append(field_name)
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    # Both callbacks should have been triggered
    assert "status" in started_fields
    assert "count" in started_fields
    assert "status" in ended_fields
    assert "count" in ended_fields


def test_large_json_random_chunks():
    """Test with a larger JSON object and various chunk sizes."""
    data = {
        "found_answer": True,
        "title": "Complete Guide",
        "sections": [
            {
                "heading": f"Section {i}",
                "content": f"This is the content for section {i} with some details.",
                "references": [{"title": f"Ref {i}", "url": f"http://example.com/{i}"}]
            }
            for i in range(5)
        ],
        "references": [{"title": "Main Ref", "url": "http://main.com"}]
    }
    json_str = json.dumps(data)
    
    captured_fields = []
    
    class TestHandler(JSONParserHandler):
        def on_field_end(self, context, field_name, value, parsed_value=None):
            captured_fields.append((field_name, value))
    
    parser = StreamingJSONParser(TestHandler())
    
    # Parse with random chunk sizes between 1 and 50 characters
    pos = 0
    random.seed(42)  # For reproducibility
    while pos < len(json_str):
        chunk_size = random.randint(1, 50)
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
    
    # Verify we captured the main title
    assert ("title", "Complete Guide") in captured_fields
    
    # Verify we captured all section headings
    for i in range(5):
        assert ("heading", f"Section {i}") in captured_fields
        assert ("content", f"This is the content for section {i} with some details.") in captured_fields


def test_search_result_article_formatting():
    """
    Comprehensive test that simulates the real use case:
    Parsing a SearchResultArticle JSON and formatting it exactly as desired.
    """
    # This is representative of what the agent returns
    data = {
        "found_answer": True,
        "title": "Monitoring Data Drift in Production with Evidently",
        "sections": [
            {
                "heading": "Monitoring Data Drift",
                "content": "To monitor data drift in production with Evidently, you can leverage the `DataDriftPreset` which evaluates shifts in data distribution between two datasets - a reference (historical) dataset and a current dataset. Here's how to set it up:\n\n1. **Prepare Your Data**: Ensure your current and reference datasets are ready for comparison. They should include non-empty columns for effective comparison.\n\n2. **Create a Report**: Use the following code to create a report:\n   ```python\n   report = Report([\n       DataDriftPreset(),\n   ])\n   my_eval = report.run(current, ref)\n   ```\n   This code runs a drift analysis comparing the current dataset against the reference dataset.\n\n3. **Enable Tests (Optional)**: You can add tests for specific pass/fail conditions for each column:\n   ```python\n   report = Report([\n       DataDriftPreset(),\n   ],\n   include_tests=True)\n   my_eval = report.run(current, ref)\n   ```\n\n4. **Analyze Results**: The `DataDriftPreset` provides insights on:\n   - **Column Drift**: Checks for shifts in distribution of each column.\n   - **Overall Dataset Drift**: Indicates the percentage of columns that have drifted. By default, if 50% of columns are considered drifted, an overall drift is reported.\n   - You can also customize drift detection methods and specify which columns to evaluate.\n\n5. **Respond to Drift**: Depending on the results, you can take actions such as retraining your model, adjusting thresholds, or implementing additional monitoring scripts.\n\nFor further customization and details on methods, check [Evidently's documentation](https://www.evidentlyai.com) on data drift detection.",
                "references": [
                    {
                        "title": "Data Drift",
                        "filename": "metrics/preset_data_drift.mdx"
                    },
                    {
                        "title": "How data drift detection works",
                        "filename": "metrics/explainer_drift.mdx"
                    }
                ]
            }
        ],
        "references": [
            {"title": "monitor data drift in production", "filename": ""},
            {"title": "how to evaluate data drift with Evidently", "filename": ""},
            {"title": "data drift detection techniques", "filename": ""}
        ]
    }
    
    json_str = json.dumps(data)
    
    # Setup parser handler that builds formatted output
    class ArticleFormatterHandler(JSONParserHandler):
        def __init__(self):
            self.output_parts = []
            self.displayed_title = False
            self.section_refs = []
            self.current_section_refs = []
        
        def on_field_end(self, path, field_name, value, parsed_value=None):
            # Root-level title
            if field_name == 'title' and path == '' and not self.displayed_title:
                self.output_parts.append(f"# {value}\n")
                self.displayed_title = True
            
            # Section heading
            elif field_name == 'heading' and 'sections' in path:
                # Save previous section's refs if any
                if self.current_section_refs:
                    self.section_refs.append(list(self.current_section_refs))
                    self.current_section_refs.clear()
                
                self.output_parts.append(f"\n## {value}\n\n")
            
            # Section content
            elif field_name == 'content' and 'sections' in path:
                unescaped = value.encode().decode('unicode_escape')
                self.output_parts.append(f"{unescaped}\n")
            
            # Section reference title
            elif field_name == 'title' and path == '/sections/references':
                self.current_section_refs.append({'title': value, 'filename': ''})
            
            # Section reference filename
            elif field_name == 'filename' and path == '/sections/references':
                if self.current_section_refs:
                    self.current_section_refs[-1]['filename'] = value
    
    handler = ArticleFormatterHandler()
    parser = StreamingJSONParser(handler)
    
    # Simulate streaming with random chunk sizes
    pos = 0
    random.seed(42)
    while pos < len(json_str):
        chunk_size = random.randint(1, 30)
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
    
    # Save last section's refs
    if handler.current_section_refs:
        handler.section_refs.append(list(handler.current_section_refs))
    
    # Add all section references collected
    if handler.section_refs:
        # Flatten all section refs into one list
        all_section_refs = []
        for refs in handler.section_refs:
            all_section_refs.extend(refs)
        
        if all_section_refs:
            handler.output_parts.append("\n\n### References\n")
            for ref in all_section_refs:
                if ref['filename']:
                    handler.output_parts.append(f"- [{ref['title']}](https://github.com/evidentlyai/docs/blob/main/{ref['filename']})\n")
                else:
                    handler.output_parts.append(f"- [{ref['title']}](https://github.com/evidentlyai/docs/blob/main/)\n")
    
    # Add root-level references
    handler.output_parts.append("\n## References\n")
    for ref in data['references']:
        title = ref['title']
        filename = ref.get('filename', '')
        if filename:
            handler.output_parts.append(f"- [{title}](https://github.com/evidentlyai/docs/blob/main/{filename})\n")
        else:
            handler.output_parts.append(f"- [{title}](https://github.com/evidentlyai/docs/blob/main/)\n")
    
    # Build the final output
    final_output = "".join(handler.output_parts)
    
    # Expected output
    expected_output = """# Monitoring Data Drift in Production with Evidently

## Monitoring Data Drift

To monitor data drift in production with Evidently, you can leverage the `DataDriftPreset` which evaluates shifts in data distribution between two datasets - a reference (historical) dataset and a current dataset. Here's how to set it up:

1. **Prepare Your Data**: Ensure your current and reference datasets are ready for comparison. They should include non-empty columns for effective comparison.

2. **Create a Report**: Use the following code to create a report:
   ```python
   report = Report([
       DataDriftPreset(),
   ])
   my_eval = report.run(current, ref)
   ```
   This code runs a drift analysis comparing the current dataset against the reference dataset.

3. **Enable Tests (Optional)**: You can add tests for specific pass/fail conditions for each column:
   ```python
   report = Report([
       DataDriftPreset(),
   ],
   include_tests=True)
   my_eval = report.run(current, ref)
   ```

4. **Analyze Results**: The `DataDriftPreset` provides insights on:
   - **Column Drift**: Checks for shifts in distribution of each column.
   - **Overall Dataset Drift**: Indicates the percentage of columns that have drifted. By default, if 50% of columns are considered drifted, an overall drift is reported.
   - You can also customize drift detection methods and specify which columns to evaluate.

5. **Respond to Drift**: Depending on the results, you can take actions such as retraining your model, adjusting thresholds, or implementing additional monitoring scripts.

For further customization and details on methods, check [Evidently's documentation](https://www.evidentlyai.com) on data drift detection.


### References
- [Data Drift](https://github.com/evidentlyai/docs/blob/main/metrics/preset_data_drift.mdx)
- [How data drift detection works](https://github.com/evidentlyai/docs/blob/main/metrics/explainer_drift.mdx)

## References
- [monitor data drift in production](https://github.com/evidentlyai/docs/blob/main/)
- [how to evaluate data drift with Evidently](https://github.com/evidentlyai/docs/blob/main/)
- [data drift detection techniques](https://github.com/evidentlyai/docs/blob/main/)
"""
    
    print("=" * 80)
    print("ACTUAL OUTPUT:")
    print("=" * 80)
    print(final_output)
    print("=" * 80)
    
    assert final_output == expected_output, f"Output mismatch!\n\nActual length: {len(final_output)}\nExpected length: {len(expected_output)}\n\nFirst difference at position: {next((i for i, (a, e) in enumerate(zip(final_output, expected_output)) if a != e), len(min(final_output, expected_output, key=len)))}"


if __name__ == "__main__":
    # Run tests manually
    test_simple_json()
    print("✅ test_simple_json passed")
    
    test_nested_json()
    print("✅ test_nested_json passed")
    
    test_random_chunk_sizes()
    print("✅ test_random_chunk_sizes passed")
    
    test_streaming_content()
    print("✅ test_streaming_content passed")
    
    test_escaped_characters()
    print("✅ test_escaped_characters passed")
    
    test_context_detection()
    print("✅ test_context_detection passed")
    
    test_parse_from_old_new()
    print("✅ test_parse_from_old_new passed")
    
    test_field_start_callback()
    print("✅ test_field_start_callback passed")
    
    test_large_json_random_chunks()
    print("✅ test_large_json_random_chunks passed")
    
    test_search_result_article_formatting()
    print("✅ test_search_result_article_formatting passed")
    
    print("\n🎉 All tests passed!")
