"""
Parser Context - Holds the parsing context buffer.

This class manages the recent context string that the parser uses
to extract complete JSON values.
"""


class Context:
    """
    Holds the recent parsing context.

    The context buffer stores all characters parsed so far, which is used
    to extract complete JSON values (objects, arrays, strings, etc.).
    """

    def __init__(self, max_size: int = 50000):
        self._content: str = ""
        self._max_size = max_size

    @property
    def content(self) -> str:
        """Get the current context content."""
        return self._content

    def append(self, char: str) -> None:
        """Add a character to the context."""
        self._content += char
        self._trim_if_needed()

    def extend(self, text: str) -> None:
        """Add multiple characters to the context."""
        self._content += text
        self._trim_if_needed()

    def _trim_if_needed(self) -> int:
        """
        Trim the context if it exceeds max size.

        Returns the number of characters that were trimmed.
        """
        if len(self._content) > self._max_size:
            trim_amount = len(self._content) - self._max_size
            self._content = self._content[-self._max_size:]
            return trim_amount
        return 0

    def __getitem__(self, key) -> str:
        """Allow indexing/slicing into the context."""
        return self._content[key]

    def __len__(self) -> int:
        """Return the length of the context."""
        return len(self._content)

    def __str__(self) -> str:
        """Return the context as a string."""
        return self._content

    def __repr__(self) -> str:
        """Return a representation of the context."""
        return f"Context({len(self._content)} chars)"
