"""
Streaming JSON Parser - Main parser class using state machine pattern.

Parse JSON incrementally using an explicit state machine where each state
is an object with a handle() method that processes characters.
"""

import json as json_module
from typing import Any, Dict, List, Tuple, Optional

from .handler import JSONParserHandler
from .context import Context
from .extractor import JSONExtractor
from .states import (
    ParserState,
    RootState,
    InObjectWaitState,
    InArrayWaitState,
)


class StreamingJSONParser:
    """
    Parse JSON incrementally using an explicit state machine.

    Each state is an object with a handle() method that processes characters
    and determines state transitions.
    """

    def __init__(self, handler: JSONParserHandler = None):
        self.handler = handler or JSONParserHandler()

        # Core state - initialize RootState with self reference
        self._state: ParserState = None
        self._previous_state: ParserState = None

        # Parsing buffers
        self._buffer: str = ""
        self._unicode_buf: str = ""

        # Context tracking
        self._context = Context()
        self._field_name: str = ""

        # Stack tracking
        self._bracket_stack: List[str] = []
        self._path_stack: List[Tuple[str, str, int]] = []

        # Position tracking
        self._array_starts: Dict[Tuple[str, str], int] = {}

        # Extractor for pulling JSON values from context
        self._extractor = JSONExtractor(self._context)

        # Initialize state after parser is fully constructed
        self._state = RootState(self)

    @property
    def state(self) -> ParserState:
        """Current parser state object."""
        return self._state

    @property
    def state_name(self) -> str:
        """Name of current state for debugging."""
        return self._state.name if self._state else "None"

    @property
    def _recent_context(self) -> str:
        """Get the recent context string (for compatibility)."""
        return str(self._context)

    # ========================================================================
    # CORE PARSING METHODS
    # ========================================================================

    def _transition(self, new_state: ParserState) -> None:
        """Transition to a new state."""
        self._previous_state = self._state
        self._state = new_state

    def _get_path(self, slice_index: int = None) -> str:
        """Get path string from path_stack."""
        stack = self._path_stack[:slice_index] if slice_index is not None else self._path_stack
        if not stack:
            return ''
        names = [entry[0] for entry in stack if entry[0]]
        return '/' + '/'.join(names)

    def _add_to_context(self, char: str) -> None:
        """Add character to recent context, managing size."""
        self._context.append(char)

        trim_amount = self._context._trim_if_needed()
        if trim_amount > 0:
            self._array_starts = {
                key: pos - trim_amount
                for key, pos in self._array_starts.items()
                if pos >= trim_amount
            }

    def _in_array(self) -> bool:
        return self._bracket_stack and self._bracket_stack[-1] == '['

    def _in_object(self) -> bool:
        return self._bracket_stack and self._bracket_stack[-1] == '{'

    def parse_incremental(self, delta: str) -> None:
        """Parse new characters incrementally."""
        if not delta:
            return

        for char in delta:
            self._add_to_context(char)
            self._state.handle(char)

    def parse_from_old_new(self, old_text: str, new_text: str) -> None:
        """Convenience method to parse delta between old and new text."""
        if not new_text.startswith(old_text):
            raise ValueError("new_text must start with old_text")
        delta = new_text[len(old_text):]
        self.parse_incremental(delta)

    # ========================================================================
    # CLOSE BRACE/BRACKET HANDLERS
    # ========================================================================

    def _handle_close_brace(self) -> None:
        """Handle closing } brace."""
        # Check if this is an object ending inside an array
        is_object_in_array = (
            len(self._bracket_stack) >= 2 and
            self._bracket_stack[-1] == '{' and
            self._bracket_stack[-2] == '['
        )

        if is_object_in_array and len(self._path_stack) >= 2:
            # Object is inside an array - get array field from path_stack
            array_field = self._path_stack[-2][0]
            path = self._get_path(-2)
            obj = self._extractor.extract_last_object()
            if obj:
                self.handler.on_array_item_end(path, array_field, item=obj)

        self._bracket_stack.pop()

        if self._path_stack and self._path_stack[-1][1] == '{':
            self._path_stack.pop()

        if self._bracket_stack:
            if self._in_array():
                self._transition(InArrayWaitState(self))
            else:
                self._transition(InObjectWaitState(self))
        else:
            self._transition(RootState(self))

    def _handle_close_bracket(self) -> None:
        """Handle closing ] bracket."""
        if (len(self._bracket_stack) >= 2 and
            self._path_stack and self._path_stack[-1][1] == '['):

            pos = len(self._context) - 2
            if pos >= 0:
                while pos >= 0 and self._context[pos] in ' \t\n\r':
                    pos -= 1
                if pos >= 0 and self._context[pos] not in '}]':
                    array_field = self._path_stack[-1][0]
                    path = self._get_path(-1)
                    item = self._extractor.extract_last_array_item()
                    if item is not None:
                        self.handler.on_array_item_end(path, array_field, item=item)

        if self._path_stack and self._path_stack[-1][1] == '[':
            field_name = self._path_stack[-1][0]
            path = self._get_path(-1)
            key = (path, field_name)
            start_pos = self._array_starts.get(key, 0)
            arr = self._extractor.extract_array_at_position(start_pos)
            arr_str = self._extractor.extract_array_string_at_position(start_pos)
            self.handler.on_field_end(path, field_name, arr_str, parsed_value=arr)
            if key in self._array_starts:
                del self._array_starts[key]
            self._path_stack.pop()

        self._bracket_stack.pop()

        if self._bracket_stack:
            if self._in_array():
                self._transition(InArrayWaitState(self))
            else:
                self._transition(InObjectWaitState(self))
        else:
            self._transition(RootState(self))

    def _check_primitive_array_item_end(self, last_char: str) -> None:
        """Check if we just finished a primitive item in an array."""
        if not self._in_array():
            return
        if not self._path_stack or self._path_stack[-1][1] != '[':
            return
        if last_char in '}]':
            return

        array_field = self._path_stack[-1][0]
        path = self._get_path(-1)
        item = self._extractor.extract_last_array_item()
        if item is not None:
            self.handler.on_array_item_end(path, array_field, item=item)

    def _check_primitive_array_item_end_on_seperator(self) -> None:
        """Check if we just finished a primitive item when comma or ] is seen."""
        if not self._in_array():
            return
        if not self._path_stack or self._path_stack[-1][1] != '[':
            return

        # Look at the character before the comma/]
        pos = len(self._context) - 2
        if pos < 0:
            return

        # Skip whitespace
        while pos >= 0 and self._context[pos] in ' \t\n\r':
            pos -= 1
        if pos < 0:
            return

        last_char = self._context[pos]

        # Don't fire for objects (}) or nested arrays (])
        if last_char in '}]':
            return

        array_field = self._path_stack[-1][0]
        path = self._get_path(-1)
        item = self._extractor.extract_last_array_item()
        if item is not None:
            self.handler.on_array_item_end(path, array_field, item=item)
