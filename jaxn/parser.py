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
    # LEGACY METHODS (kept for backward compatibility, now delegated to states)
    # ========================================================================

    def _handle_close_brace(self) -> None:
        """Handle closing } brace - delegated to states module."""
        from .states import handle_close_brace
        handle_close_brace(self)

    def _handle_close_bracket(self) -> None:
        """Handle closing ] bracket - delegated to states module."""
        from .states import handle_close_bracket
        handle_close_bracket(self)

    def _check_primitive_array_item_end(self, last_char: str) -> None:
        """Check if we just finished a primitive item in an array - delegated to states."""
        from .states import check_primitive_array_item_end
        check_primitive_array_item_end(self, last_char)

    def _check_primitive_array_item_end_on_seperator(self) -> None:
        """Check primitive array item end on separator - delegated to states."""
        from .states import check_primitive_array_item_end_on_seperator
        check_primitive_array_item_end_on_seperator(self)
