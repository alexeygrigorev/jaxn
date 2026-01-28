"""
JSON Extractor - Utilities for extracting JSON values from context.

This class provides methods to extract JSON objects, arrays, and primitives
from the parsed context buffer.
"""

import json as json_module
from typing import Any, Dict, List, Optional

from .context import Context


class JSONExtractor:
    """
    Extract JSON values from a context object.

    This class is used by the parser to extract complete JSON values
    (objects, arrays, strings, primitives) from the recent context.
    """

    def __init__(self, context: Context):
        self.context = context

    def extract_last_object(self) -> Optional[Dict]:
        """Extract the last complete JSON object from the context."""
        bracket_count = 0
        start_pos = -1

        for i in range(len(self.context) - 1, -1, -1):
            ch = self.context[i]
            if ch == '}':
                bracket_count += 1
            elif ch == '{':
                bracket_count -= 1
                if bracket_count == 0:
                    start_pos = i
                    break

        if start_pos < 0:
            return None

        bracket_count = 0
        end_pos = start_pos
        for i in range(start_pos, len(self.context)):
            ch = self.context[i]
            if ch == '{':
                bracket_count += 1
            elif ch == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_pos = i + 1
                    break

        try:
            return json_module.loads(self.context[start_pos:end_pos])
        except:
            return None

    def extract_last_array_item(self) -> Any:
        """Extract the last item from an array (object, array, string, or primitive)."""
        if not self.context:
            return None

        pos = len(self.context) - 1
        while pos >= 0 and self.context[pos] in ',] \t\n\r':
            pos -= 1
        if pos < 0:
            return None

        last_char = self.context[pos]

        if last_char == '}':
            return self.extract_last_object()

        if last_char == ']':
            return self._extract_nested_array(pos)

        if last_char == '"':
            return self._extract_quoted_string(pos)

        return self._extract_primitive(pos)

    def _extract_nested_array(self, pos: int) -> Optional[List]:
        """Extract a nested array ending at position pos."""
        bracket_count = 0
        start_pos = -1
        for i in range(pos, -1, -1):
            ch = self.context[i]
            if ch == ']':
                bracket_count += 1
            elif ch == '[':
                bracket_count -= 1
                if bracket_count == 0:
                    start_pos = i
                    break
        if start_pos >= 0:
            try:
                return json_module.loads(self.context[start_pos:pos + 1])
            except:
                return None
        return None

    def _extract_quoted_string(self, pos: int) -> Optional[str]:
        """Extract a quoted string ending at position pos."""
        escape_next = False
        start_pos = pos
        for i in range(pos - 1, -1, -1):
            ch = self.context[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                start_pos = i
                break
        try:
            return json_module.loads(self.context[start_pos:pos + 1])
        except:
            return None

    def _extract_primitive(self, pos: int) -> Any:
        """Extract a primitive value (number, boolean, null) ending at position pos."""
        end_pos = pos + 1
        start_pos = pos
        while start_pos > 0:
            ch = self.context[start_pos - 1]
            if ch in ',:[ \t\n\r':
                break
            start_pos -= 1

        json_str = self.context[start_pos:end_pos].strip()
        if not json_str:
            return None
        try:
            return json_module.loads(json_str)
        except:
            return None

    def extract_array_at_position(self, start_pos: int) -> Optional[List]:
        """
        Extract a complete array starting at the given position.

        Finds the matching closing bracket and returns the parsed array.
        """
        bracket_count = 0
        end_pos = len(self.context)
        in_string = False
        escape_next = False

        for i in range(start_pos, len(self.context)):
            ch = self.context[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '[':
                    bracket_count += 1
                elif ch == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i + 1
                        break

        try:
            return json_module.loads(self.context[start_pos:end_pos])
        except:
            return None

    def extract_array_string_at_position(self, start_pos: int) -> str:
        """
        Extract the inner content of an array as a string.

        Returns the content between the opening and closing brackets.
        """
        bracket_count = 0
        end_pos = len(self.context)
        in_string = False
        escape_next = False

        for i in range(start_pos, len(self.context)):
            ch = self.context[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '[':
                    bracket_count += 1
                elif ch == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i + 1
                        break

        return self.context[start_pos + 1:end_pos - 1] if end_pos > start_pos + 1 else ""
