"""
Streaming JSON Parser - Main parser class using state machine pattern.

Parse JSON incrementally using an explicit state machine where each state
is an object with a handle() method that processes characters.
"""

from typing import Dict

from .handler import JSONParserHandler
from .context import Context
from .extractor import JSONExtractor
from .stack_tracker import StackTracker
from .states import ParserState, RootState


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

        # Stack tracking - now managed by StackTracker
        self._stacks = StackTracker()

        # Position tracking
        self._array_starts: Dict[tuple, int] = {}

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

    # Expose stack tracker methods for backward compatibility with states
    @property
    def _bracket_stack(self):
        return self._stacks.bracket_stack

    @property
    def _path_stack(self):
        return self._stacks.path_stack

    def _in_array(self):
        return self._stacks.in_array()

    def _in_object(self):
        return self._stacks.in_object()

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
        return self._stacks.get_path(slice_index)

    def _get_field_name(self) -> str:
        """Get the current field name."""
        # If we're in an array, use the array's field name from path_stack
        if self._stacks.in_array() and self._stacks.path_stack:
            return self._stacks.path_stack[-1][0]
        # Otherwise use the current field name
        return self._field_name

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
