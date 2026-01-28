"""
Streaming JSON Parser - A SAX-style JSON parser for incomplete streams.

This module provides the main API for the streaming JSON parser.
"""

from .handler import JSONParserHandler
from .parser import StreamingJSONParser

__all__ = [
    'StreamingJSONParser',
    'JSONParserHandler',
]
