r"""
Buffers - Manages parsing buffers.

This class holds the temporary buffers used during JSON parsing
for accumulating field names, string values, and escape sequences.
"""


class Buffers:
    r"""
    Manages parsing buffers.

    The buffer is used to accumulate characters during parsing,
    such as field names, string values, and primitive values.
    The unicode buffer is used specifically for accumulating
    the 4 hex digits of unicode escape sequences (\uXXXX).
    """

    def __init__(self):
        self._buffer: str = ""
        self._unicode_buf: str = ""

    @property
    def buffer(self) -> str:
        """Get the main parsing buffer."""
        return self._buffer

    @buffer.setter
    def buffer(self, value: str) -> None:
        """Set the main parsing buffer."""
        self._buffer = value

    @property
    def unicode_buffer(self) -> str:
        """Get the unicode escape sequence buffer."""
        return self._unicode_buf

    @unicode_buffer.setter
    def unicode_buffer(self, value: str) -> None:
        """Set the unicode escape sequence buffer."""
        self._unicode_buf = value

    def append_to_buffer(self, char: str) -> None:
        """Add a character to the main buffer."""
        self._buffer += char

    def append_to_unicode_buffer(self, char: str) -> None:
        """Add a character to the unicode buffer."""
        self._unicode_buf += char

    def clear_buffer(self) -> None:
        """Clear the main buffer."""
        self._buffer = ""

    def clear_unicode_buffer(self) -> None:
        """Clear the unicode buffer."""
        self._unicode_buf = ""

    def clear_all(self) -> None:
        """Clear all buffers."""
        self._buffer = ""
        self._unicode_buf = ""
