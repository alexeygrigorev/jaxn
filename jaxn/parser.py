"""
Streaming JSON Parser - Main parser class using state machine pattern.

Parse JSON incrementally using an explicit state machine where each state
is an object with a handle() method that processes characters.
"""

from .buffers import Buffers
from .handler import JSONParserHandler
from .tracker import Tracker
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
        self.buffers = Buffers()

        # All tracking state (brackets, paths, context, extractor)
        self.tracker = Tracker()

        # Initialize state after parser is fully constructed
        self._state = RootState(self)

    @property
    def state(self) -> ParserState:
        """Current parser state object."""
        return self._state

    @property
    def _extractor(self):
        """Get the JSON extractor from tracker."""
        return self.tracker.extractor

    # ========================================================================
    # CORE PARSING METHODS
    # ========================================================================

    def _transition(self, new_state: ParserState) -> None:
        """Transition to a new state."""
        self._previous_state = self._state
        self._state = new_state

    def parse_incremental(self, delta: str) -> None:
        """Parse new characters incrementally."""
        if not delta:
            return

        for char in delta:
            self.tracker.append_to_context(char)
            self._state.handle(char)

    def parse_from_old_new(self, old_text: str, new_text: str) -> None:
        """Convenience method to parse delta between old and new text."""
        if not new_text.startswith(old_text):
            raise ValueError("new_text must start with old_text")
        delta = new_text[len(old_text):]
        self.parse_incremental(delta)
