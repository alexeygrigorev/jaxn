"""Extensive test coverage for parsed values with complex nested structures."""

from jaxn import StreamingJSONParser, JSONParserHandler
import json
import random


def test_deeply_nested_objects():
    """Test parsing deeply nested objects with multiple levels."""
    data = {
        "company": {
            "name": "TechCorp",
            "departments": [
                {
                    "name": "Engineering",
                    "teams": [
                        {
                            "name": "Backend",
                            "members": [
                                {"name": "Alice", "role": "Lead", "skills": ["Python", "Go"]},
                                {"name": "Bob", "role": "Developer", "skills": ["Java", "Kotlin"]}
                            ]
                        },
                        {
                            "name": "Frontend",
                            "members": [
                                {"name": "Charlie", "role": "Lead", "skills": ["React", "TypeScript"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Sales",
                    "teams": [
                        {
                            "name": "Enterprise",
                            "members": [
                                {"name": "Diana", "role": "Manager", "skills": ["Negotiation"]}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    json_str = json.dumps(data)
    
    collected_members = []
    collected_teams = []
    collected_departments = []
    
    class NestedHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'members':
                    collected_members.append(item.copy())
                elif field_name == 'teams':
                    collected_teams.append(item.copy())
                elif field_name == 'departments':
                    collected_departments.append(item.copy())
    
    handler = NestedHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify members
    assert len(collected_members) == 4
    assert collected_members[0]['name'] == "Alice"
    assert collected_members[0]['skills'] == ["Python", "Go"]
    assert collected_members[3]['name'] == "Diana"
    
    # Verify teams
    assert len(collected_teams) == 3
    assert collected_teams[0]['name'] == "Backend"
    assert len(collected_teams[0]['members']) == 2
    assert collected_teams[2]['name'] == "Enterprise"
    
    # Verify departments
    assert len(collected_departments) == 2
    assert collected_departments[0]['name'] == "Engineering"
    assert len(collected_departments[0]['teams']) == 2


def test_mixed_nested_arrays_and_objects():
    """Test complex structure with mixed arrays and objects at various levels."""
    data = {
        "project": "DataPipeline",
        "config": {
            "stages": [
                {
                    "name": "Extract",
                    "sources": [
                        {"type": "database", "connection": {"host": "db1", "port": 5432}},
                        {"type": "api", "connection": {"url": "https://api.example.com", "timeout": 30}}
                    ]
                },
                {
                    "name": "Transform",
                    "operations": [
                        {"type": "filter", "rules": [{"field": "age", "op": ">", "value": 18}]},
                        {"type": "aggregate", "rules": [{"field": "total", "op": "sum"}]}
                    ]
                }
            ]
        }
    }
    
    json_str = json.dumps(data)
    
    collected_sources = []
    collected_operations = []
    collected_stages = []
    
    class MixedHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'sources':
                    collected_sources.append(item.copy())
                elif field_name == 'operations':
                    collected_operations.append(item.copy())
                elif field_name == 'stages':
                    collected_stages.append(item.copy())
    
    handler = MixedHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify sources
    assert len(collected_sources) == 2
    assert collected_sources[0]['type'] == "database"
    assert collected_sources[0]['connection']['host'] == "db1"
    assert collected_sources[1]['connection']['timeout'] == 30
    
    # Verify operations
    assert len(collected_operations) == 2
    assert collected_operations[0]['type'] == "filter"
    assert len(collected_operations[0]['rules']) == 1
    assert collected_operations[0]['rules'][0]['field'] == "age"
    
    # Verify stages
    assert len(collected_stages) == 2
    assert collected_stages[0]['name'] == "Extract"
    assert len(collected_stages[0]['sources']) == 2


def test_array_of_arrays():
    """Test parsing arrays containing other arrays."""
    data = {
        "matrix": [
            {"row": 0, "values": [1, 2, 3]},
            {"row": 1, "values": [4, 5, 6]},
            {"row": 2, "values": [7, 8, 9]}
        ],
        "tags": [
            {"category": "tech", "items": ["python", "javascript", "rust"]},
            {"category": "design", "items": ["figma", "sketch"]}
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_matrix = []
    collected_tags = []
    
    class ArrayHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'matrix':
                    collected_matrix.append(item.copy())
                elif field_name == 'tags':
                    collected_tags.append(item.copy())
    
    handler = ArrayHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Verify matrix
    assert len(collected_matrix) == 3
    assert collected_matrix[0]['values'] == [1, 2, 3]
    assert collected_matrix[2]['values'] == [7, 8, 9]
    
    # Verify tags
    assert len(collected_tags) == 2
    assert collected_tags[0]['items'] == ["python", "javascript", "rust"]
    assert len(collected_tags[1]['items']) == 2


def test_empty_and_null_values():
    """Test handling of empty arrays, objects, and null values."""
    data = {
        "items": [
            {"id": 1, "data": {}, "tags": [], "note": None},
            {"id": 2, "data": {"key": "value"}, "tags": ["tag1"], "note": "Important"},
            {"id": 3, "data": {}, "tags": [], "note": None}
        ],
        "metadata": {
            "empty_list": [],
            "empty_obj": {},
            "null_value": None
        }
    }
    
    json_str = json.dumps(data)
    
    collected_items = []
    
    class EmptyHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'items':
                collected_items.append(item.copy())
    
    handler = EmptyHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(collected_items) == 3
    assert collected_items[0]['data'] == {}
    assert collected_items[0]['tags'] == []
    assert collected_items[0]['note'] is None
    assert collected_items[1]['data'] == {"key": "value"}
    assert collected_items[1]['tags'] == ["tag1"]


def test_streaming_complex_structure():
    """Test character-by-character streaming with complex nested structure."""
    data = {
        "response": {
            "status": "success",
            "results": [
                {
                    "id": 1,
                    "metadata": {
                        "created": "2024-01-01",
                        "tags": ["urgent", "reviewed"]
                    },
                    "nested": {
                        "level": 2,
                        "items": [
                            {"name": "item1", "value": 100},
                            {"name": "item2", "value": 200}
                        ]
                    }
                },
                {
                    "id": 2,
                    "metadata": {
                        "created": "2024-01-02",
                        "tags": ["pending"]
                    },
                    "nested": {
                        "level": 1,
                        "items": [
                            {"name": "item3", "value": 300}
                        ]
                    }
                }
            ]
        }
    }
    
    json_str = json.dumps(data)
    
    collected_results = []
    collected_nested_items = []
    
    class StreamHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'results':
                    collected_results.append(item.copy())
                elif field_name == 'items':
                    collected_nested_items.append(item.copy())
    
    handler = StreamHandler()
    parser = StreamingJSONParser(handler)
    
    # Stream character by character
    for char in json_str:
        parser.parse_incremental(char)
    
    assert len(collected_results) == 2
    assert collected_results[0]['id'] == 1
    assert collected_results[0]['metadata']['tags'] == ["urgent", "reviewed"]
    assert collected_results[0]['nested']['level'] == 2
    assert len(collected_results[0]['nested']['items']) == 2
    
    assert len(collected_nested_items) == 3
    assert collected_nested_items[0]['name'] == "item1"
    assert collected_nested_items[2]['value'] == 300


def test_random_chunk_sizes_complex():
    """Test with random chunk sizes on complex nested structure."""
    data = {
        "catalog": {
            "categories": [
                {
                    "name": "Electronics",
                    "subcategories": [
                        {
                            "name": "Laptops",
                            "products": [
                                {"id": 1, "name": "MacBook Pro", "specs": {"ram": 16, "storage": 512}},
                                {"id": 2, "name": "Dell XPS", "specs": {"ram": 32, "storage": 1024}}
                            ]
                        },
                        {
                            "name": "Phones",
                            "products": [
                                {"id": 3, "name": "iPhone", "specs": {"ram": 8, "storage": 256}}
                            ]
                        }
                    ]
                },
                {
                    "name": "Books",
                    "subcategories": [
                        {
                            "name": "Fiction",
                            "products": [
                                {"id": 4, "name": "1984", "specs": {"pages": 328, "year": 1949}}
                            ]
                        }
                    ]
                }
            ]
        }
    }
    
    json_str = json.dumps(data)
    
    collected_products = []
    collected_subcategories = []
    collected_categories = []
    
    class ChunkHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item:
                if field_name == 'products':
                    collected_products.append(item.copy())
                elif field_name == 'subcategories':
                    collected_subcategories.append(item.copy())
                elif field_name == 'categories':
                    collected_categories.append(item.copy())
    
    handler = ChunkHandler()
    parser = StreamingJSONParser(handler)
    
    # Parse with random chunk sizes
    pos = 0
    random.seed(123)
    while pos < len(json_str):
        chunk_size = random.randint(1, 50)
        chunk = json_str[pos:pos + chunk_size]
        parser.parse_incremental(chunk)
        pos += chunk_size
    
    # Verify products
    assert len(collected_products) == 4
    assert collected_products[0]['name'] == "MacBook Pro"
    assert collected_products[0]['specs']['ram'] == 16
    assert collected_products[3]['name'] == "1984"
    
    # Verify subcategories
    assert len(collected_subcategories) == 3
    assert collected_subcategories[0]['name'] == "Laptops"
    assert len(collected_subcategories[0]['products']) == 2
    
    # Verify categories
    assert len(collected_categories) == 2
    assert collected_categories[0]['name'] == "Electronics"
    assert len(collected_categories[0]['subcategories']) == 2


def test_special_characters_in_nested_objects():
    """Test parsing with special characters and escapes in nested structures."""
    data = {
        "documents": [
            {
                "title": "Line 1\nLine 2",
                "metadata": {
                    "author": "O'Brien",
                    "description": "Quote: \"Hello\" and Tab:\there"
                },
                "tags": ["new\nline", "tab\there"]
            },
            {
                "title": "Path: C:\\Users\\file.txt",
                "metadata": {
                    "author": "Smith",
                    "description": "Backslash: \\ and Forward: /"
                },
                "tags": ["path\\separator"]
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_documents = []
    
    class SpecialCharHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'documents':
                collected_documents.append(item.copy())
    
    handler = SpecialCharHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(collected_documents) == 2
    assert "Line 1\nLine 2" in collected_documents[0]['title']
    assert collected_documents[0]['metadata']['author'] == "O'Brien"
    assert '"' in collected_documents[0]['metadata']['description']
    assert '\t' in collected_documents[0]['metadata']['description']
    assert "C:\\Users\\file.txt" in collected_documents[1]['title']


def test_numeric_and_boolean_values():
    """Test parsing objects with various numeric and boolean types."""
    data = {
        "records": [
            {
                "id": 1,
                "score": 95.5,
                "active": True,
                "verified": False,
                "nullable": None,
                "zero": 0,
                "negative": -42
            },
            {
                "id": 2,
                "score": 0.0,
                "active": False,
                "verified": True,
                "nullable": None,
                "zero": 0,
                "negative": -100
            }
        ]
    }
    
    json_str = json.dumps(data)
    
    collected_records = []
    
    class TypeHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'records':
                collected_records.append(item.copy())
    
    handler = TypeHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    assert len(collected_records) == 2
    assert collected_records[0]['id'] == 1
    assert collected_records[0]['score'] == 95.5
    assert collected_records[0]['active'] is True
    assert collected_records[0]['verified'] is False
    assert collected_records[0]['nullable'] is None
    assert collected_records[0]['zero'] == 0
    assert collected_records[0]['negative'] == -42


def test_very_deep_nesting():
    """Test extremely deep nesting levels."""
    data = {
        "level1": {
            "items": [
                {
                    "level2": {
                        "items": [
                            {
                                "level3": {
                                    "items": [
                                        {
                                            "level4": {
                                                "items": [
                                                    {"id": 1, "value": "deep"},
                                                    {"id": 2, "value": "deeper"}
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    
    json_str = json.dumps(data)
    
    all_items = []
    
    class DeepHandler(JSONParserHandler):
        def on_array_item_end(self, path, field_name, item=None):
            if item and field_name == 'items':
                all_items.append((path, item.copy()))
    
    handler = DeepHandler()
    parser = StreamingJSONParser(handler)
    parser.parse_incremental(json_str)
    
    # Should collect items at all nesting levels
    # level1/items, level1/items/level2/items, level1/items/level2/items/level3/items,
    # level1/items/level2/items/level3/items/level4/items (2 leaf objects)
    assert len(all_items) == 5
    
    # The deepest items should have id and value (the leaf objects)
    deepest_items = [item for path, item in all_items if 'id' in item]
    assert len(deepest_items) == 2
    assert deepest_items[0]['value'] == "deep"
    assert deepest_items[1]['value'] == "deeper"
    
    # Verify we have all nesting levels represented
    paths = [path for path, item in all_items]
    assert any('/level1' in p and '/level2' not in p for p in paths)  # level1 items
    assert any('/level2' in p and '/level3' not in p for p in paths)  # level2 items  
    assert any('/level3' in p and '/level4' not in p for p in paths)  # level3 items
    assert any('/level4' in p for p in paths)  # level4 items (the leaf objects)
