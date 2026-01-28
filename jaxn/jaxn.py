"""
Streaming JSON Parser - A SAX-style JSON parser for incomplete streams.

This module now uses the state machine implementation for clarity.
"""

from .state_machine import StreamingJSONParser

from typing import Any


class JSONParserHandler:
    """
    Base handler class for JSON parsing events.
    Clients should subclass this and override the methods they need.
    """
    
    def on_field_start(self, path: str, field_name: str) -> None:
        """
        Called when starting to read a field value.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the field being read
        """
        pass
    
    def on_field_end(self, path: str, field_name: str, value: str, parsed_value: Any = None) -> None:
        """
        Called when a field value is complete.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the field
            value: Complete value of the field (as string from JSON)
            parsed_value: Parsed value (dict for objects, list for arrays, actual value for primitives)
        """
        pass
    
    def on_value_chunk(self, path: str, field_name: str, chunk: str) -> None:
        """
        Called for each character as string values stream in.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the field being streamed
            chunk: Single character chunk
        """
        pass
    
    def on_array_item_start(self, path: str, field_name: str) -> None:
        """
        Called when starting a new object in an array.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the array field
        """
        pass
    
    def on_array_item_end(self, path: str, field_name: str, item: Any = None) -> None:
        """
        Called when finishing an object in an array.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the array field
            item: The complete parsed item for this array element
        """
        pass


__all__ = [
    'StreamingJSONParser',
    'JSONParserHandler',
]
