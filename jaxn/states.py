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

def handle_close_brace(tracker, extractor, handler, parser) -> None:
    """Handle closing } brace - used by multiple states."""

    if tracker.is_object_in_array() and len(tracker.path_stack) >= 2:
        # Object is inside an array - get array field from path_stack
        array_field = tracker.path_stack[-2][0]
        path = tracker.get_path(-2)
        obj = extractor.extract_last_object()
        if obj:
            handler.on_array_item_end(path, array_field, item=obj)

    tracker.bracket_stack.pop()

    if tracker.at_object_level():
        tracker.path_stack.pop()

    if tracker.has_brackets():
        if tracker.in_array():
            parser._transition(InArrayWaitState(parser))
        else:
            parser._transition(InObjectWaitState(parser))
    else:
        parser._transition(RootState(parser))


def handle_close_bracket(tracker, extractor, handler, parser) -> None:
    """Handle closing ] bracket - used by multiple states."""

    if (len(tracker.bracket_stack) >= 2 and
        tracker.at_array_level()):

        pos = len(tracker) - 2
        if pos >= 0:
            while pos >= 0 and tracker[pos] in ' \t\n\r':
                pos -= 1
            if pos >= 0 and tracker[pos] not in '}]':
                array_field = tracker.path_stack[-1][0]
                path = tracker.get_path(-1)
                item = extractor.extract_last_array_item()
                if item is not None:
                    handler.on_array_item_end(path, array_field, item=item)

    if tracker.at_array_level():
        field_name = tracker.path_stack[-1][0]
        path = tracker.get_path(-1)
        key = (path, field_name)
        start_pos = tracker.array_starts.get(key, 0)
        arr = extractor.extract_array_at_position(start_pos)
        arr_str = extractor.extract_array_string_at_position(start_pos)
        handler.on_field_end(path, field_name, arr_str, parsed_value=arr)
        if key in tracker.array_starts:
            del tracker.array_starts[key]
        tracker.path_stack.pop()

    tracker.bracket_stack.pop()

    if tracker.has_brackets():
        if tracker.in_array():
            parser._transition(InArrayWaitState(parser))
        else:
            parser._transition(InObjectWaitState(parser))
    else:
        parser._transition(RootState(parser))


def check_primitive_array_item_end(tracker, extractor, handler, last_char: str) -> None:
    """Check if we just finished a primitive item in an array."""
    if not tracker.in_array():
        return
    if not tracker.at_array_level():
        return
    if last_char in '}]':
        return

    array_field = tracker.path_stack[-1][0]
    path = tracker.get_path(-1)
    item = extractor.extract_last_array_item()
    if item is not None:
        handler.on_array_item_end(path, array_field, item=item)


def check_primitive_array_item_end_on_seperator(tracker, extractor, handler) -> None:
    """Check if we just finished a primitive item when comma or ] is seen."""
    if not tracker.in_array():
        return
    if not tracker.at_array_level():
        return

    # Look at the character before the comma/]
    pos = len(tracker) - 2
    if pos < 0:
        return

    # Skip whitespace
    while pos >= 0 and tracker[pos] in ' \t\n\r':
        pos -= 1
    if pos < 0:
        return

    last_char = tracker[pos]

    # Don't fire for objects (}) or nested arrays (])
    if last_char in '}]':
        return

    array_field = tracker.path_stack[-1][0]
    path = tracker.get_path(-1)
    item = extractor.extract_last_array_item()
    if item is not None:
        handler.on_array_item_end(path, array_field, item=item)


# ========================================================================
# BASE STATE CLASS
# ========================================================================

class ParserState:
    """Base class for parser states."""

    def __init__(self, parser: 'StreamingJSONParser'):
        self.parser = parser
        self.tracker = parser.tracker
        self.handler = parser.handler
        self.buffers = parser.buffers

    def handle(self, char: str) -> None:
        """Handle a character. Subclasses must implement."""
        raise NotImplementedError


# ========================================================================
# CONCRETE STATE CLASSES
# ========================================================================

class RootState(ParserState):
    """Initial state or between top-level values."""

    def handle(self, char: str) -> None:
        if char in ' \t\n\r':
            return
        if char == '{':
            self._handle_open_brace()
        elif char == '[':
            self._handle_open_bracket()

    def _handle_open_brace(self) -> None:
        self.tracker.bracket_stack.append('{')
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_open_bracket(self) -> None:
        self.tracker.bracket_stack.append('[')
        self.parser._transition(InArrayWaitState(self.parser))


class FieldNameState(ParserState):
    """Parsing a field name (before colon)."""

    def handle(self, char: str) -> None:
        if char == '\\':
            self._handle_escape()
        elif char == '"':
            self._handle_end_quote()
        else:
            self.buffers.append_to_buffer(char)

    def _handle_escape(self) -> None:
        self.parser._transition(EscapeState(self.parser))

    def _handle_end_quote(self) -> None:
        # The buffer now contains decoded characters (escape sequences processed)
        self.tracker.field_name = self.buffers.buffer
        self.buffers.clear_buffer()
        self.parser._transition(AfterFieldNameState(self.parser))


class AfterFieldNameState(ParserState):
    """Just finished field name, expecting colon."""

    def handle(self, char: str) -> None:
        if char == ':':
            self._handle_colon()
        elif char not in ' \t\n\r':
            pass  # Invalid JSON, ignore

    def _handle_colon(self) -> None:
        self.parser._transition(AfterColonState(self.parser))


class AfterColonState(ParserState):
    """Just saw colon, expecting value."""

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
        self.handler.on_field_start(self.tracker.get_path(), self.tracker.field_name)
        self.buffers.clear_buffer()
        self.parser._transition(ValueStringState(self.parser))

    def _handle_object_start(self) -> None:
        self.handler.on_field_start(self.tracker.get_path(), self.tracker.field_name)
        self.tracker.path_stack.append((self.tracker.field_name, '{', len(self.tracker.bracket_stack)))
        self.tracker.bracket_stack.append('{')
        self.tracker.field_name = ""
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_array_start(self) -> None:
        path = self.tracker.get_path()
        self.handler.on_field_start(path, self.tracker.field_name)

        key = (path, self.tracker.field_name)
        self.tracker.array_starts[key] = len(self.tracker) - 1

        self.tracker.path_stack.append((self.tracker.field_name, '[', len(self.tracker.bracket_stack)))
        self.tracker.bracket_stack.append('[')
        self.tracker.field_name = ""
        self.parser._transition(InArrayWaitState(self.parser))

    def _handle_primitive_start(self, char: str) -> None:
        self.handler.on_field_start(self.tracker.get_path(), self.tracker.field_name)
        self.buffers.buffer = char
        self.parser._transition(PrimitiveState(self.parser))


class ValueStringState(ParserState):
    """Inside a string value."""

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
        raw = self.buffers.buffer

        try:
            parsed = json_module.loads('"' + raw + '"')
        except:
            parsed = raw

        # Only call on_field_end if we're NOT in an array
        # Strings in arrays are items, not field values
        if not self.tracker.in_array():
            path = self.tracker.get_path()
            field = self.tracker.field_name
            self.handler.on_field_end(path, field, raw, parsed_value=parsed)
            self.tracker.field_name = ""

        self.buffers.clear_buffer()

        if self.tracker.in_array():
            self.parser._transition(InArrayWaitState(self.parser))
        else:
            self.parser._transition(InObjectWaitState(self.parser))

    def _handle_regular_char(self, char: str) -> None:
        self.buffers.append_to_buffer(char)
        path = self.tracker.get_path()
        field = self.tracker.get_current_field_name()
        self.handler.on_value_chunk(path, field, char)


class PrimitiveState(ParserState):
    """Parsing a number, boolean, or null."""

    def handle(self, char: str) -> None:
        if char in ',}]\t\n\r ':
            self._handle_value_end(char)
        elif char == '"':
            self.buffers.append_to_buffer(char)
        else:
            self.buffers.append_to_buffer(char)

    def _handle_value_end(self, char: str) -> None:
        raw = self.buffers.buffer.strip()

        try:
            parsed = json_module.loads(raw)
        except:
            parsed = raw

        # Only call on_field_end if we're NOT in an array
        # Primitives in arrays are items, not field values
        if not self.tracker.in_array():
            path = self.tracker.get_path()
            field = self.tracker.field_name
            self.handler.on_field_end(path, field, raw, parsed_value=parsed)
            self.tracker.field_name = ""

        self.buffers.clear_buffer()

        if char == ',':
            if self.tracker.in_array() and raw:
                check_primitive_array_item_end(
                    self.tracker,
                    self.parser._extractor,
                    self.handler,
                    raw[-1]
                )
            self._transition_to_wait_state()
        elif char == '}':
            handle_close_brace(
                self.tracker,
                self.parser._extractor,
                self.handler,
                self.parser
            )
        elif char == ']':
            handle_close_bracket(
                self.tracker,
                self.parser._extractor,
                self.handler,
                self.parser
            )

    def _transition_to_wait_state(self) -> None:
        if self.tracker.in_array():
            self.parser._transition(InArrayWaitState(self.parser))
        else:
            self.parser._transition(InObjectWaitState(self.parser))


class InObjectWaitState(ParserState):
    """Inside an object, waiting for field name or end."""

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
        self.buffers.clear_buffer()
        self.parser._transition(FieldNameState(self.parser))

    def _handle_close_brace(self) -> None:
        handle_close_brace(
            self.tracker,
            self.parser._extractor,
            self.handler,
            self.parser
        )


class InArrayWaitState(ParserState):
    """Inside an array, waiting for value or end."""

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
        check_primitive_array_item_end_on_seperator(
            self.tracker,
            self.parser._extractor,
            self.handler
        )

    def _handle_close_bracket(self) -> None:
        handle_close_bracket(
            self.tracker,
            self.parser._extractor,
            self.handler,
            self.parser
        )

    def _handle_string_start(self) -> None:
        self.buffers.clear_buffer()
        self.parser._transition(ValueStringState(self.parser))

    def _handle_object_start(self) -> None:
        if self.tracker.at_array_level():
            array_field = self.tracker.path_stack[-1][0]
            path = self.tracker.get_path(-1)
            self.handler.on_array_item_start(path, array_field)

        self.tracker.bracket_stack.append('{')
        self.tracker.path_stack.append(('', '{', len(self.tracker.bracket_stack) - 1))
        self.parser._transition(InObjectWaitState(self.parser))

    def _handle_array_start(self) -> None:
        self.tracker.bracket_stack.append('[')
        self.tracker.path_stack.append(('', '[', len(self.tracker.bracket_stack) - 1))
        self.parser._transition(InArrayWaitState(self.parser))

    def _handle_primitive_start(self, char: str) -> None:
        if self.tracker.at_array_level():
            array_field = self.tracker.path_stack[-1][0]
            path = self.tracker.get_path(-1)
            self.handler.on_field_start(path, array_field)
        self.buffers.buffer = char
        self.parser._transition(PrimitiveState(self.parser))


class EscapeState(ParserState):
    """Processing escape sequence \\X."""

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
        was_in_field_name = isinstance(self.parser._previous_state, FieldNameState)

        # Decode the escape sequence
        decoded = self._ESCAPE_MAP.get(char, char)

        if was_in_value:
            # For value strings, add raw to buffer but also send decoded chunk
            self.buffers.append_to_buffer('\\' + char)
            path = self.tracker.get_path()
            field = self.tracker.get_current_field_name()
            self.handler.on_value_chunk(path, field, decoded)
        elif was_in_field_name:
            # For field names, add decoded directly to buffer
            self.buffers.append_to_buffer(decoded)
        else:
            # Fallback - add raw escape
            self.buffers.append_to_buffer('\\' + char)

        self._transition_back(was_in_value, was_in_field_name)

    def _handle_unicode_escape(self) -> None:
        self.buffers.clear_unicode_buffer()
        self.buffers.append_to_buffer('\\u')
        # Remember the state before EscapeState (the actual string/field name state)
        self.parser._unicode_escape_source = self.parser._previous_state
        self.parser._transition(UnicodeEscapeState(self.parser))

    def _transition_back(self, was_in_value: bool, was_in_field_name: bool) -> None:
        if was_in_value:
            self.parser._transition(ValueStringState(self.parser))
        elif was_in_field_name:
            self.parser._transition(FieldNameState(self.parser))
        else:
            self.parser._transition(FieldNameState(self.parser))


class UnicodeEscapeState(ParserState):
    """Processing unicode escape \\uXXXX."""

    def handle(self, char: str) -> None:
        self.buffers.append_to_buffer(char)
        self.buffers.append_to_unicode_buffer(char)

        if len(self.buffers.unicode_buffer) == 4:
            self._process_escape_sequence()

    def _process_escape_sequence(self) -> None:
        # Use the saved source state from when we entered EscapeState
        source_state = getattr(self.parser, '_unicode_escape_source', self.parser._previous_state)
        was_in_field_name = isinstance(source_state, FieldNameState)
        was_in_value = isinstance(source_state, ValueStringState)

        try:
            code_point = int(self.buffers.unicode_buffer, 16)
            decoded = chr(code_point)
        except:
            decoded = None

        if decoded is not None:
            self._handle_valid_escape(decoded, was_in_value)
        else:
            self._handle_invalid_escape(was_in_value)

        self.buffers.clear_unicode_buffer()
        # Clean up the saved state
        if hasattr(self.parser, '_unicode_escape_source'):
            delattr(self.parser, '_unicode_escape_source')

        # Transition back to the appropriate state
        if was_in_field_name:
            self.parser._transition(FieldNameState(self.parser))
        else:
            self.parser._transition(ValueStringState(self.parser))

    def _handle_valid_escape(self, decoded: str, was_in_value: bool) -> None:
        # Replace the \uXXXX in buffer with decoded character
        current_buffer = self.buffers.buffer
        self.buffers.buffer = current_buffer[:-6] + decoded

        if was_in_value:
            # For value strings, send decoded chunk to handler
            path = self.tracker.get_path()
            field = self.tracker.get_current_field_name()
            self.handler.on_value_chunk(path, field, decoded)

    def _handle_invalid_escape(self, was_in_value: bool) -> None:
        if was_in_value:
            # For value strings, send individual characters to handler
            path = self.tracker.get_path()
            field = self.tracker.get_current_field_name()
            self.handler.on_value_chunk(path, field, '\\')
            self.handler.on_value_chunk(path, field, 'u')
            for c in self.buffers.unicode_buffer:
                self.handler.on_value_chunk(path, field, c)
