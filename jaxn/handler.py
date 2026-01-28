"""
JSON Parser Handler - Base handler class for JSON parsing events.

Clients should subclass this and override the methods they need.
"""

from typing import Any


class JSONParserHandler:
    """
    Base handler class for JSON parsing events.
    Clients should subclass this and override the methods they need.
    """

    def on_field_start(self, path: str, field_name: str) -> None:
        """Called when starting to read a field value."""
        pass

    def on_field_end(self, path: str, field_name: str, value: str, parsed_value: Any = None) -> None:
        """Called when a field value is complete."""
        pass

    def on_value_chunk(self, path: str, field_name: str, chunk: str) -> None:
        """Called for each character as string values stream in."""
        pass

    def on_array_item_start(self, path: str, field_name: str) -> None:
        """Called when starting a new object in an array."""
        pass

    def on_array_item_end(self, path: str, field_name: str, item: Any = None) -> None:
        """Called when finishing an item in an array."""
        pass
