"""
Tracker - Manages all state during JSON parsing.

This class tracks:
- Bracket stack ({} and [] nesting)
- Path stack (field names for building paths)
- Array start positions
- Current field name being parsed
- Context buffer for value extraction
"""

from typing import TYPE_CHECKING, Dict, List, Tuple

if TYPE_CHECKING:
    from .extractor import JSONExtractor


def _create_extractor(tracker):
    """Create extractor lazily to avoid circular import."""
    from .extractor import JSONExtractor
    return JSONExtractor(tracker)


class Tracker:
    """
    Manages all parsing state including brackets, paths, fields, and context.

    The bracket_stack tracks nesting of {} and [].
    The path_stack tracks field names and types for building paths.
    The context buffer stores characters for value extraction.
    """

    def __init__(self, max_size: int = 50000):
        # Bracket and path tracking
        self._bracket_stack: List[str] = []
        self._path_stack: List[Tuple[str, str, int]] = []
        self._array_starts: Dict[Tuple[str, str], int] = {}
        self._field_name: str = ""

        # Context buffer for extraction
        self._content: str = ""
        self._max_size = max_size
        self._extractor = None

    # ========================================================================
    # BRACKET AND PATH TRACKING
    # ========================================================================

    @property
    def bracket_stack(self) -> List[str]:
        """Get the bracket stack (for direct access)."""
        return self._bracket_stack

    @property
    def path_stack(self) -> List[Tuple[str, str, int]]:
        """Get the path stack (for direct access)."""
        return self._path_stack

    @property
    def array_starts(self) -> Dict[Tuple[str, str], int]:
        """Get the array starts dictionary."""
        return self._array_starts

    @property
    def field_name(self) -> str:
        """Get the current field name being parsed."""
        return self._field_name

    @field_name.setter
    def field_name(self, value: str) -> None:
        """Set the current field name being parsed."""
        self._field_name = value

    def push_bracket(self, bracket: str) -> None:
        """Push a bracket ({ or [) onto the stack."""
        self._bracket_stack.append(bracket)

    def pop_bracket(self) -> str:
        """Pop and return the top bracket from the stack."""
        return self._bracket_stack.pop()

    def peek_bracket(self) -> str:
        """Return the top bracket without popping."""
        return self._bracket_stack[-1] if self._bracket_stack else ''

    def push_path(self, field_name: str, bracket_type: str, depth: int) -> None:
        """Push a path entry onto the stack."""
        self._path_stack.append((field_name, bracket_type, depth))

    def pop_path(self) -> Tuple[str, str, int]:
        """Pop and return the top path entry from the stack."""
        return self._path_stack.pop()

    def in_array(self) -> bool:
        """Check if we're currently inside an array."""
        return self._bracket_stack and self._bracket_stack[-1] == '['

    def in_object(self) -> bool:
        """Check if we're currently inside an object."""
        return self._bracket_stack and self._bracket_stack[-1] == '{'

    def at_array_level(self) -> bool:
        """
        Check if we're at an array level in the path stack.

        This is true when path_stack has entries and the top entry
        represents an array (bracket_type == '[').
        """
        return self._path_stack and self._path_stack[-1][1] == '['

    def get_path(self, slice_index: int = None) -> str:
        """
        Get path string from path_stack.

        Args:
            slice_index: If provided, only use this many entries from the stack.
        """
        stack = self._path_stack[:slice_index] if slice_index is not None else self._path_stack
        if not stack:
            return ''
        names = [entry[0] for entry in stack if entry[0]]
        return '/' + '/'.join(names)

    def get_current_field_name(self) -> str:
        """
        Get the current field name for callbacks.

        If we're in an array, returns the array's field name from path_stack.
        Otherwise returns the current field name being parsed.
        """
        if self.in_array() and self._path_stack:
            return self._path_stack[-1][0]
        return self._field_name

    # ========================================================================
    # CONTEXT BUFFER TRACKING
    # ========================================================================

    @property
    def content(self) -> str:
        """Get the current context content."""
        return self._content

    @property
    def extractor(self) -> 'JSONExtractor':
        """Get the JSON extractor for this tracker."""
        if self._extractor is None:
            self._extractor = _create_extractor(self)
        return self._extractor

    def append_to_context(self, char: str) -> int:
        """
        Add a character to the context.

        Returns:
            The number of characters trimmed (0 if none).
        """
        self._content += char
        trim_amount = self._trim_context_if_needed()
        if trim_amount > 0:
            self._adjust_array_starts(trim_amount)
        return trim_amount

    def _trim_context_if_needed(self) -> int:
        """
        Trim the context if it exceeds max size.

        Returns:
            The number of characters that were trimmed.
        """
        if len(self._content) > self._max_size:
            trim_amount = len(self._content) - self._max_size
            self._content = self._content[-self._max_size:]
            return trim_amount
        return 0

    def _adjust_array_starts(self, trim_amount: int) -> None:
        """
        Adjust array start positions after context trimming.

        Args:
            trim_amount: Number of characters that were trimmed
        """
        # Update in-place by clearing and re-populating
        to_keep = {}
        for key, pos in self._array_starts.items():
            if pos >= trim_amount:
                to_keep[key] = pos - trim_amount
        self._array_starts.clear()
        self._array_starts.update(to_keep)

    # ========================================================================
    # DUCK-TYPING INTERFACE FOR EXTRACTOR
    # ========================================================================

    def __getitem__(self, key) -> str:
        """Allow indexing/slicing into the context (for extractor)."""
        return self._content[key]

    def __len__(self) -> int:
        """Return the length of the context (for extractor)."""
        return len(self._content)

    def __str__(self) -> str:
        """Return the context as a string."""
        return self._content

    def __repr__(self) -> str:
        """Return a representation of the tracker."""
        return f"Tracker({len(self._content)} chars, {len(self._bracket_stack)} brackets)"
