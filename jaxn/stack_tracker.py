"""
Stack Tracker - Manages bracket and path stacks for JSON parsing.

This class tracks the nesting structure of JSON being parsed,
including the current field path and whether we're in an object or array.
"""

from typing import List, Tuple


class StackTracker:
    """
    Manages bracket and path stacks during JSON parsing.

    The bracket_stack tracks nesting of {} and [].
    The path_stack tracks field names and types for building paths.
    """

    def __init__(self):
        self._bracket_stack: List[str] = []
        self._path_stack: List[Tuple[str, str, int]] = []

    @property
    def bracket_stack(self) -> List[str]:
        """Get the bracket stack (for direct access)."""
        return self._bracket_stack

    @property
    def path_stack(self) -> List[Tuple[str, str, int]]:
        """Get the path stack (for direct access)."""
        return self._path_stack

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

    def get_current_array_field(self) -> str:
        """
        Get the field name of the current array (if in one).

        Returns the field name from the top of path_stack if we're in an array.
        """
        if self.in_array() and self._path_stack:
            return self._path_stack[-1][0]
        return ''
