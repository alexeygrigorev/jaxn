"""
Parser State Classes - Each state handles characters and determines transitions.

This provides a clean, object-oriented state machine pattern for JSON parsing.
"""

import json as json_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import StreamingJSONParser


# ========================================================================
# SHARED HELPER FUNCTIONS
# ========================================================================

def handle_close_brace(parser) -> None:
    """Handle closing } brace - used by multiple states."""
    from .states import InArrayWaitState, InObjectWaitState, RootState

    # Check if this is an object ending inside an array
    is_object_in_array = (
        len(parser._bracket_stack) >= 2 and
        parser._bracket_stack[-1] == '{' and
        parser._bracket_stack[-2] == '['
    )

    if is_object_in_array and len(parser._path_stack) >= 2:
        # Object is inside an array - get array field from path_stack
        array_field = parser._path_stack[-2][0]
        path = parser._get_path(-2)
        obj = parser._extractor.extract_last_object()
        if obj:
            parser.handler.on_array_item_end(path, array_field, item=obj)

    parser._bracket_stack.pop()

    if parser._path_stack and parser._path_stack[-1][1] == '{':
        parser._path_stack.pop()

    if parser._bracket_stack:
        if parser._in_array():
            parser._transition(InArrayWaitState(parser))
        else:
            parser._transition(InObjectWaitState(parser))
    else:
        parser._transition(RootState(parser))


def handle_close_bracket(parser) -> None:
    """Handle closing ] bracket - used by multiple states."""
    from .states import InArrayWaitState, InObjectWaitState, RootState

    if (len(parser._bracket_stack) >= 2 and
        parser._path_stack and parser._path_stack[-1][1] == '['):

        pos = len(parser._context) - 2
        if pos >= 0:
            while pos >= 0 and parser._context[pos] in ' \t\n\r':
                pos -= 1
            if pos >= 0 and parser._context[pos] not in '}]':
                array_field = parser._path_stack[-1][0]
                path = parser._get_path(-1)
                item = parser._extractor.extract_last_array_item()
                if item is not None:
                    parser.handler.on_array_item_end(path, array_field, item=item)

    if parser._path_stack and parser._path_stack[-1][1] == '[':
        field_name = parser._path_stack[-1][0]
        path = parser._get_path(-1)
        key = (path, field_name)
        start_pos = parser._array_starts.get(key, 0)
        arr = parser._extractor.extract_array_at_position(start_pos)
        arr_str = parser._extractor.extract_array_string_at_position(start_pos)
        parser.handler.on_field_end(path, field_name, arr_str, parsed_value=arr)
        if key in parser._array_starts:
            del parser._array_starts[key]
        parser._path_stack.pop()

    parser._bracket_stack.pop()

    if parser._bracket_stack:
        if parser._in_array():
            parser._transition(InArrayWaitState(parser))
        else:
            parser._transition(InObjectWaitState(parser))
    else:
        parser._transition(RootState(parser))


def check_primitive_array_item_end(parser, last_char: str) -> None:
    """Check if we just finished a primitive item in an array."""
    if not parser._in_array():
        return
    if not parser._path_stack or parser._path_stack[-1][1] != '[':
        return
    if last_char in '}]':
        return

    array_field = parser._path_stack[-1][0]
    path = parser._get_path(-1)
    item = parser._extractor.extract_last_array_item()
    if item is not None:
        parser.handler.on_array_item_end(path, array_field, item=item)


def check_primitive_array_item_end_on_seperator(parser) -> None:
    """Check if we just finished a primitive item when comma or ] is seen."""
    if not parser._in_array():
        return
    if not parser._path_stack or parser._path_stack[-1][1] != '[':
        return

    # Look at the character before the comma/]
    pos = len(parser._context) - 2
    if pos < 0:
        return

    # Skip whitespace
    while pos >= 0 and parser._context[pos] in ' \t\n\r':
        pos -= 1
    if pos < 0:
        return

    last_char = parser._context[pos]

    # Don't fire for objects (}) or nested arrays (])
    if last_char in '}]':
        return

    array_field = parser._path_stack[-1][0]
    path = parser._get_path(-1)
    item = parser._extractor.extract_last_array_item()
    if item is not None:
        parser.handler.on_array_item_end(path, array_field, item=item)


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
            self._handle_open_brace()
        elif char == '[':
            self._handle_open_bracket()

    def _handle_open_brace(self) -> None:
        self.parser._bracket_stack.append('{')
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_open_bracket(self) -> None:
        self.parser._bracket_stack.append('[')
        self.parser._transition(InArrayWaitState(self.parser))


class FieldNameState(ParserState):
    """Parsing a field name (before colon)."""

    name = "FIELD_NAME"

    def handle(self, char: str) -> None:
        if char == '\\':
            self._handle_escape()
        elif char == '"':
            self._handle_end_quote()
        else:
            self.parser._buffer += char

    def _handle_escape(self) -> None:
        self.parser._transition(EscapeState(self.parser))

    def _handle_end_quote(self) -> None:
        try:
            self.parser._field_name = json_module.loads('"' + self.parser._buffer + '"')
        except:
            self.parser._field_name = self.parser._buffer
        self.parser._buffer = ""
        self.parser._transition(AfterFieldNameState(self.parser))


class AfterFieldNameState(ParserState):
    """Just finished field name, expecting colon."""

    name = "AFTER_FIELD_NAME"

    def handle(self, char: str) -> None:
        if char == ':':
            self._handle_colon()
        elif char not in ' \t\n\r':
            pass  # Invalid JSON, ignore

    def _handle_colon(self) -> None:
        self.parser._transition(AfterColonState(self.parser))


class AfterColonState(ParserState):
    """Just saw colon, expecting value."""

    name = "AFTER_COLON"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == '"':
            self._handle_string_start()
        elif char == '{':
            self._handle_object_start()
        elif char == '[':
            self._handle_array_start()
        elif char.isdigit() or char in 'tfn-':
            self._handle_primitive_start(char)

    def _handle_string_start(self) -> None:
        self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
        self.parser._buffer = ""
        self.parser._transition(ValueStringState(self.parser))

    def _handle_object_start(self) -> None:
        self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
        self.parser._path_stack.append((self.parser._field_name, '{', len(self.parser._bracket_stack)))
        self.parser._bracket_stack.append('{')
        self.parser._field_name = ""
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_array_start(self) -> None:
        path = self.parser._get_path()
        self.parser.handler.on_field_start(path, self.parser._field_name)

        key = (path, self.parser._field_name)
        self.parser._array_starts[key] = len(self.parser._recent_context) - 1

        self.parser._path_stack.append((self.parser._field_name, '[', len(self.parser._bracket_stack)))
        self.parser._bracket_stack.append('[')
        self.parser._field_name = ""
        self.parser._transition(InArrayWaitState(self.parser))

    def _handle_primitive_start(self, char: str) -> None:
        self.parser.handler.on_field_start(self.parser._get_path(), self.parser._field_name)
        self.parser._buffer = char
        self.parser._transition(PrimitiveState(self.parser))


class ValueStringState(ParserState):
    """Inside a string value."""

    name = "VALUE_STRING"

    def handle(self, char: str) -> None:
        if char == '\\':
            self._handle_escape()
        elif char == '"':
            self._handle_end_quote()
        else:
            self._handle_regular_char(char)

    def _handle_escape(self) -> None:
        self.parser._transition(EscapeState(self.parser))

    def _handle_end_quote(self) -> None:
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

    def _handle_regular_char(self, char: str) -> None:
        self.parser._buffer += char
        path = self.parser._get_path()
        field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name
        self.parser.handler.on_value_chunk(path, field, char)


class PrimitiveState(ParserState):
    """Parsing a number, boolean, or null."""

    name = "PRIMITIVE"

    def handle(self, char: str) -> None:
        if char in ',}]\t\n\r ':
            self._handle_value_end(char)
        elif char == '"':
            self.parser._buffer += char
        else:
            self.parser._buffer += char

    def _handle_value_end(self, char: str) -> None:
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
                check_primitive_array_item_end(self.parser, raw[-1])
            self._transition_to_wait_state()
        elif char == '}':
            handle_close_brace(self.parser)
        elif char == ']':
            handle_close_bracket(self.parser)

    def _transition_to_wait_state(self) -> None:
        if self.parser._in_array():
            self.parser._transition(InArrayWaitState(self.parser))
        else:
            self.parser._transition(InObjectWaitState(self.parser))


class InObjectWaitState(ParserState):
    """Inside an object, waiting for field name or end."""

    name = "IN_OBJECT_WAIT"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == '"':
            self._handle_field_start()
        elif char == '}':
            self._handle_close_brace()
        elif char == ',':
            pass  # Ready for next field

    def _handle_field_start(self) -> None:
        self.parser._buffer = ""
        self.parser._transition(FieldNameState(self.parser))

    def _handle_close_brace(self) -> None:
        handle_close_brace(self.parser)


class InArrayWaitState(ParserState):
    """Inside an array, waiting for value or end."""

    name = "IN_ARRAY_WAIT"

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == ',':
            self._handle_comma()
        elif char == ']':
            self._handle_close_bracket()
        elif char == '"':
            self._handle_string_start()
        elif char == '{':
            self._handle_object_start()
        elif char == '[':
            self._handle_array_start()
        elif char.isdigit() or char in 'tfn-':
            self._handle_primitive_start(char)

    def _handle_comma(self) -> None:
        check_primitive_array_item_end_on_seperator(self.parser)

    def _handle_close_bracket(self) -> None:
        handle_close_bracket(self.parser)

    def _handle_string_start(self) -> None:
        self.parser._buffer = ""
        self.parser._transition(ValueStringState(self.parser))

    def _handle_object_start(self) -> None:
        if self.parser._path_stack and self.parser._path_stack[-1][1] == '[':
            array_field = self.parser._path_stack[-1][0]
            path = self.parser._get_path(-1)
            self.parser.handler.on_array_item_start(path, array_field)

        self.parser._bracket_stack.append('{')
        self.parser._path_stack.append(('', '{', len(self.parser._bracket_stack) - 1))
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_array_start(self) -> None:
        self.parser._bracket_stack.append('[')
        self.parser._path_stack.append(('', '[', len(self.parser._bracket_stack) - 1))
        self.parser._transition(InArrayWaitState(self.parser))

    def _handle_primitive_start(self, char: str) -> None:
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
        if char == 'u':
            self._handle_unicode_escape()
            return

        was_in_value = isinstance(self.parser._previous_state, ValueStringState)

        self.parser._buffer += '\\' + char

        if was_in_value:
            decoded = self._ESCAPE_MAP.get(char, char)
            path = self.parser._get_path()
            field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name
            self.parser.handler.on_value_chunk(path, field, decoded)

        self._transition_back(was_in_value)

    def _handle_unicode_escape(self) -> None:
        self.parser._unicode_buf = ""
        self.parser._buffer += '\\u'
        self.parser._transition(UnicodeEscapeState(self.parser))

    def _transition_back(self, was_in_value: bool) -> None:
        if was_in_value:
            self.parser._transition(ValueStringState(self.parser))
        else:
            self.parser._transition(FieldNameState(self.parser))


class UnicodeEscapeState(ParserState):
    """Processing unicode escape \\uXXXX."""

    name = "UNICODE_ESCAPE"

    def handle(self, char: str) -> None:
        self.parser._buffer += char
        self.parser._unicode_buf += char

        if len(self.parser._unicode_buf) == 4:
            self._process_escape_sequence()

    def _process_escape_sequence(self) -> None:
        try:
            code_point = int(self.parser._unicode_buf, 16)
            decoded = chr(code_point)
        except:
            decoded = None

        path = self.parser._get_path()
        field = self.parser._path_stack[-1][0] if self.parser._in_array() and self.parser._path_stack else self.parser._field_name

        if decoded is not None:
            self._handle_valid_escape(path, field, decoded)
        else:
            self._handle_invalid_escape(path, field)

        self.parser._unicode_buf = ""
        self.parser._transition(ValueStringState(self.parser))

    def _handle_valid_escape(self, path: str, field: str, decoded: str) -> None:
        self.parser.handler.on_value_chunk(path, field, decoded)
        self.parser._buffer = self.parser._buffer[:-6] + decoded

    def _handle_invalid_escape(self, path: str, field: str) -> None:
        self.parser.handler.on_value_chunk(path, field, '\\')
        self.parser.handler.on_value_chunk(path, field, 'u')
        for c in self.parser._unicode_buf:
            self.parser.handler.on_value_chunk(path, field, c)
