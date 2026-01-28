"""
Parser State Classes - Each state handles characters and determines transitions.

This provides a clean, object-oriented state machine pattern for JSON parsing.
"""

import json as json_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import StreamingJSONParser


# ========================================================================
# BASE STATE CLASS
# ========================================================================

class ParserState:
    """Base class for parser states."""

    name = "base"

    def __init__(self, parser: 'StreamingJSONParser' = None):
        self.parser = parser

    def handle(self, char: str) -> None:
        """Handle a character. Subclasses must implement."""
        raise NotImplementedError


# ========================================================================
# CONCRETE STATE CLASSES
# ========================================================================

class RootState(ParserState):
    """Initial state or between top-level values."""

    name = "ROOT"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == '{':
            self.parser._bracket_stack.append('{')
            self.parser._transition(InObjectWaitState(self.parser))
        elif char == '[':
            self.parser._bracket_stack.append('[')
            self.parser._transition(InArrayWaitState(self.parser))


class FieldNameState(ParserState):
    """Parsing a field name (before colon)."""

    name = "FIELD_NAME"

    def handle(self, char: str) -> None:
        if char == '\\':
            self.parser._transition(EscapeState(self.parser))
        elif char == '"':
            # Field name complete
            try:
                self.parser._field_name = json_module.loads('"' + self.parser._buffer + '"')
            except:
                self.parser._field_name = self.parser._buffer
            self.parser._buffer = ""
            self.parser._transition(AfterFieldNameState(self.parser))
        else:
            self.parser._buffer += char


class AfterFieldNameState(ParserState):
    """Just finished field name, expecting colon."""

    name = "AFTER_FIELD_NAME"

    def handle(self, char: str) -> None:
        if char == ':':
            self.parser._transition(AfterColonState(self.parser))
        elif char not in ' \t\n\r':
            pass  # Invalid JSON, ignore


class AfterColonState(ParserState):
    """Just saw colon, expecting value."""

    name = "AFTER_COLON"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return

        if char == '"':
            self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
            self.parser._buffer = ""
            self.parser._transition(ValueStringState(self.parser))
        elif char == '{':
            self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
            self.parser._path_stack.append((self.parser._field_name, '{', len(self.parser._bracket_stack)))
            self.parser._bracket_stack.append('{')
            self.parser._field_name = ""
            self.parser._transition(InObjectWaitState(self.parser))
        elif char == '[':
            path = self.parser._get_path()
            self.parser.handler.on_field_start(path, self.parser._field_name)

            key = (path, self.parser._field_name)
            self.parser._array_starts[key] = len(self.parser._recent_context) - 1

            self.parser._path_stack.append((self.parser._field_name, '[', len(self.parser._bracket_stack)))
            self.parser._bracket_stack.append('[')
            self.parser._field_name = ""
            self.parser._transition(InArrayWaitState(self.parser))
        elif char.isdigit() or char in 'tfn-':
            self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
            self.parser._buffer = char
            self.parser._transition(PrimitiveState(self.parser))


class ValueStringState(ParserState):
    """Inside a string value."""

    name = "VALUE_STRING"

    def handle(self, char: str) -> None:
        if char == '\\':
            self.parser._transition(EscapeState(self.parser))
        elif char == '"':
            raw = self.parser._buffer

            try:
                parsed = json_module.loads('"' + raw + '"')
            except:
                parsed = raw

            # Only call on_field_end if we're NOT in an array
            # Strings in arrays are items, not field values
            if not self.parser._in_array():
                path = self.parser._get_path()
                field = self.parser._field_name
                self.parser.handler.on_field_end(path, field, raw, parsed_value=parsed)
                self.parser._field_name = ""

            self.parser._buffer = ""

            if self.parser._in_array():
                self.parser._transition(InArrayWaitState(self.parser))
            else:
                self.parser._transition(InObjectWaitState(self.parser))
        else:
            self.parser._buffer += char
            path = self.parser._get_path()
            field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name
            self.parser.handler.on_value_chunk(path, field, char)


class PrimitiveState(ParserState):
    """Parsing a number, boolean, or null."""

    name = "PRIMITIVE"

    def handle(self, char: str) -> None:
        if char in ',}]\t\n\r ':
            raw = self.parser._buffer.strip()

            try:
                parsed = json_module.loads(raw)
            except:
                parsed = raw

            # Only call on_field_end if we're NOT in an array
            # Primitives in arrays are items, not field values
            if not self.parser._in_array():
                path = self.parser._get_path()
                field = self.parser._field_name
                self.parser.handler.on_field_end(path, field, raw, parsed_value=parsed)
                self.parser._field_name = ""

            self.parser._buffer = ""

            if char == ',':
                if self.parser._in_array() and raw:
                    self.parser._check_primitive_array_item_end(raw[-1])
                if self.parser._in_array():
                    self.parser._transition(InArrayWaitState(self.parser))
                else:
                    self.parser._transition(InObjectWaitState(self.parser))
            elif char == '}':
                self.parser._handle_close_brace()
            elif char == ']':
                self.parser._handle_close_bracket()
        elif char == '"':
            self.parser._buffer += char
        else:
            self.parser._buffer += char


class InObjectWaitState(ParserState):
    """Inside an object, waiting for field name or end."""

    name = "IN_OBJECT_WAIT"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == '"':
            self.parser._buffer = ""
            self.parser._transition(FieldNameState(self.parser))
        elif char == '}':
            self.parser._handle_close_brace()
        elif char == ',':
            pass  # Ready for next field


class InArrayWaitState(ParserState):
    """Inside an array, waiting for value or end."""

    name = "IN_ARRAY_WAIT"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == ',':
            # Check if previous item was a primitive (string, number, boolean, null)
            # and trigger on_array_item_end for it
            self.parser._check_primitive_array_item_end_on_seperator()
        elif char == ']':
            # _handle_close_bracket already handles the last item
            self.parser._handle_close_bracket()
        elif char == '"':
            self.parser._buffer = ""
            self.parser._transition(ValueStringState(self.parser))
        elif char == '{':
            if self.parser._path_stack and self.parser._path_stack[-1][1] == '[':
                array_field = self.parser._path_stack[-1][0]
                path = self.parser._get_path(-1)
                self.parser.handler.on_array_item_start(path, array_field)

            self.parser._bracket_stack.append('{')
            self.parser._path_stack.append(('', '{', len(self.parser._bracket_stack) - 1))
            self.parser._transition(InObjectWaitState(self.parser))
        elif char == '[':
            self.parser._bracket_stack.append('[')
            self.parser._path_stack.append(('', '[', len(self.parser._bracket_stack) - 1))
            self.parser._transition(InArrayWaitState(self.parser))
        elif char.isdigit() or char in 'tfn-':
            # Fire on_field_start for primitive values in arrays
            if self.parser._path_stack and self.parser._path_stack[-1][1] == '[':
                array_field = self.parser._path_stack[-1][0]
                path = self.parser._get_path(-1)
                self.parser.handler.on_field_start(path, array_field)
            self.parser._buffer = char
            self.parser._transition(PrimitiveState(self.parser))


class EscapeState(ParserState):
    """Processing escape sequence \\X."""

    name = "ESCAPE"

    _ESCAPE_MAP = {
        'n': '\n', 't': '\t', 'r': '\r',
        '\\': '\\', '"': '"', '/': '/',
        'b': '\b', 'f': '\f',
    }

    def handle(self, char: str) -> None:
        was_in_value = isinstance(self.parser._previous_state, ValueStringState)

        if char == 'u':
            self.parser._unicode_buf = ""
            self.parser._buffer += '\\u'
            self.parser._transition(UnicodeEscapeState(self.parser))
            return

        self.parser._buffer += '\\' + char

        if was_in_value:
            decoded = self._ESCAPE_MAP.get(char, char)
            path = self.parser._get_path()
            field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name
            self.parser.handler.on_value_chunk(path, field, decoded)

        if was_in_value:
            self.parser._transition(ValueStringState(self.parser))
        else:
            self.parser._transition(FieldNameState(self.parser))


class UnicodeEscapeState(ParserState):
    """Processing unicode escape \\uXXXX."""

    name = "UNICODE_ESCAPE"

    def handle(self, char: str) -> None:
        # Add the hex digit to buffer (we'll replace the whole sequence later)
        self.parser._buffer += char
        self.parser._unicode_buf += char

        if len(self.parser._unicode_buf) == 4:
            try:
                code_point = int(self.parser._unicode_buf, 16)
                decoded = chr(code_point)
            except:
                decoded = None

            # Send decoded character to handler
            path = self.parser._get_path()
            field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name

            if decoded is not None:
                # Valid escape - send the decoded character
                self.parser.handler.on_value_chunk(path, field, decoded)
                # Replace the \uXXXX in buffer with the decoded character
                self.parser._buffer = self.parser._buffer[:-6] + decoded
            else:
                # Invalid escape - send the original \uXXXX characters as-is
                # We need to send \, u, and the 4 hex digits
                self.parser.handler.on_value_chunk(path, field, '\\')
                self.parser.handler.on_value_chunk(path, field, 'u')
                for c in self.parser._unicode_buf:
                    self.parser.handler.on_value_chunk(path, field, c)

            self.parser._unicode_buf = ""
            self.parser._transition(ValueStringState(self.parser))
