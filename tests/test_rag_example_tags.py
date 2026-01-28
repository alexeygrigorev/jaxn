

from typing import Any, Dict
from jaxn import JSONParserHandler, StreamingJSONParser


raw_json = """
{
    "answer": "To use an LLM (Large Language Model) as a judge, you can...",
    "followup_questions": [
        "What are the requirements to set up an LLM judge?",
        "Can you explain the evaluation dataset creation process?",
        "What is the purpose of a verbosity evaluator?"
    ],
    "numbers": [1, 2, 3, 4, 5]
}
""".strip()

class CapturingArrayItemEndHandler(JSONParserHandler):

    def __init__(self):
        self.items = []

    def on_array_item_end(self, path: str, field_name: str, item: Dict[str, Any] = None):
        self.items.append((path, field_name, item))


def test_rag_response_handler():
    handler = CapturingArrayItemEndHandler()
    parser = StreamingJSONParser(handler)

    for chunk in raw_json:
        parser.parse_incremental(chunk)

    # Expected: 3 strings from followup_questions + 5 numbers from numbers array
    expected_items = [
        ('', 'followup_questions', 'What are the requirements to set up an LLM judge?'),
        ('', 'followup_questions', 'Can you explain the evaluation dataset creation process?'),
        ('', 'followup_questions', 'What is the purpose of a verbosity evaluator?'),
        ('', 'numbers', 1),
        ('', 'numbers', 2),
        ('', 'numbers', 3),
        ('', 'numbers', 4),
        ('', 'numbers', 5),
    ]

    assert handler.items == expected_items
