# jaxn

A SAX-style JSON parser for processing incomplete JSON streams character-by-character.

## Overview

**jaxn** is a lightweight streaming JSON parser that processes JSON incrementally as it arrives, similar to how SAX parsers work with XML. Instead of waiting for the complete JSON document, jaxn fires callbacks as it encounters different parts of the JSON structure, making it perfect for:

- Real-time streaming applications (e.g., LLM responses, API streams)
- Processing large JSON files without loading them entirely into memory
- Displaying content as it arrives rather than waiting for complete responses
- Building responsive UIs that update progressively

## Installation

```bash
pip install jaxn
```

## Quick Start

Here's a simple example that prints field values as they're parsed:

```python
from jaxn import StreamingJSONParser, JSONParserHandler

class SimpleHandler(JSONParserHandler):
    def on_field_end(self, path, field_name, value, parsed_value=None):
        print(f"{field_name}: {value}")

handler = SimpleHandler()
parser = StreamingJSONParser(handler)

# Process JSON incrementally
json_data = '{"name": "Alice", "age": 30}'
parser.parse_incremental(json_data)
```

## Detailed Example: Streaming Markdown Renderer

This example shows how to convert a streaming JSON response into formatted markdown output in real-time. The example is based on the demo in the `demo/` directory.

### The JSON Structure

```json
{
    "title": "Monitoring Data Drift in Production",
    "sections": [
        {
            "heading": "Overview",
            "content": "Monitoring data drift is crucial...",
            "references": [
                {
                    "title": "Data Drift",
                    "filename": "metrics/preset_data_drift.mdx"
                }
            ]
        }
    ]
}
```

### The Handler Implementation

```python
from pathlib import Path
from jaxn import StreamingJSONParser, JSONParserHandler
import time

class SearchResultHandler(JSONParserHandler):
    def on_field_start(self, path: str, field_name: str):
        # Print references header when we encounter a references array
        if field_name == "references":
            level = path.count("/") + 2
            print(f"\n{'#' * level} References\n")

    def on_field_end(self, path, field_name, value, parsed_value=None):
        # Print title as main heading
        if field_name == "title" and path == "/":
            print(f"# {value}")
        # Print section headings
        elif field_name == "heading":
            print(f"\n\n## {value}\n")
        # Add spacing after content
        elif field_name == "content":
            print("\n")

    def on_value_chunk(self, path, field_name, chunk):
        # Stream content character by character for real-time display
        if field_name == "content":
            print(chunk, end="", flush=True)

    def on_array_item_end(self, path, field_name, item=None):
        # Print references as markdown links
        if field_name == "references":
            title = item.get("title", "")
            filename = item.get("filename", "")
            print(f"- [{title}]({filename})")

# Use the handler
handler = SearchResultHandler()
parser = StreamingJSONParser(handler)

# Simulate streaming by processing JSON in small chunks
json_message = Path('message.json').read_text(encoding='utf-8')
for i in range(0, len(json_message), 4):
    chunk = json_message[i:i+4]
    parser.parse_incremental(chunk)
    time.sleep(0.01)  # Simulate network delay
```

### Output

The above code produces formatted markdown output that appears progressively:

```markdown
# Monitoring Data Drift in Production

## Overview

Monitoring data drift is crucial to understanding the health and performance of machine learning models in production...

### References

- [Data Drift](metrics/preset_data_drift.mdx)
- [How data drift detection works](metrics/explainer_drift.mdx)
- [Overview](docs/platform/monitoring_overview.mdx)
```

## API Reference

### JSONParserHandler

Base handler class for JSON parsing events. Subclass this and override the methods you need.

#### Methods

**`on_field_start(path: str, field_name: str) -> None`**

Called when starting to read a field value.

- `path`: Path to current location (e.g., "/sections/references")
- `field_name`: Name of the field being read

**`on_field_end(path: str, field_name: str, value: str, parsed_value: Any = None) -> None`**

Called when a field value is complete.

- `path`: Path to current location
- `field_name`: Name of the field
- `value`: Complete value of the field (as string from JSON)
- `parsed_value`: Parsed value (dict for objects, list for arrays, actual value for primitives)

**`on_value_chunk(path: str, field_name: str, chunk: str) -> None`**

Called for each character as string values stream in. Perfect for displaying content in real-time.

- `path`: Path to current location
- `field_name`: Name of the field being streamed
- `chunk`: Single character chunk

**`on_array_item_start(path: str, field_name: str) -> None`**

Called when starting a new object in an array.

- `path`: Path to current location
- `field_name`: Name of the array field

**`on_array_item_end(path: str, field_name: str, item: Dict[str, Any] = None) -> None`**

Called when finishing an object in an array.

- `path`: Path to current location
- `field_name`: Name of the array field
- `item`: The complete parsed dictionary for this array item

### StreamingJSONParser

Parse JSON incrementally as it streams in, character by character.

#### Methods

**`__init__(handler: JSONParserHandler = None)`**

Initialize the parser with a handler for events.

- `handler`: JSONParserHandler instance to receive parsing events

**`parse_incremental(delta: str) -> None`**

Parse new characters added since last call. Fires callbacks as events are detected.

- `delta`: New characters to parse (string)

**`parse_from_old_new(old_text: str, new_text: str) -> None`**

Convenience method that calculates the delta between old and new text.

- `old_text`: Previously processed text
- `new_text`: New text (should start with old_text)

## Use Cases

### 1. Real-time LLM Response Display

Display streaming responses from Large Language Models as they're generated:

```python
class LLMDisplayHandler(JSONParserHandler):
    def on_value_chunk(self, path, field_name, chunk):
        if field_name == "content":
            print(chunk, end="", flush=True)

parser = StreamingJSONParser(LLMDisplayHandler())
# Feed chunks as they arrive from the LLM API
```

### 2. Progress Tracking

Track progress through large JSON structures:

```python
class ProgressHandler(JSONParserHandler):
    def __init__(self):
        self.items_processed = 0
    
    def on_array_item_end(self, path, field_name, item=None):
        self.items_processed += 1
        print(f"Processed {self.items_processed} items...")
```

### 3. Selective Field Extraction

Extract only the fields you need without parsing the entire document:

```python
class FieldExtractor(JSONParserHandler):
    def __init__(self):
        self.titles = []
    
    def on_field_end(self, path, field_name, value, parsed_value=None):
        if field_name == "title":
            self.titles.append(value)
```

## License

WTFPL - Do What The Fuck You Want To Public License

## Links

- **GitHub**: https://github.com/alexeygrigorev/jaxn
- **Issues**: https://github.com/alexeygrigorev/jaxn/issues