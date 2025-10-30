"""
Streaming JSON Parser - A SAX-style JSON parser for incomplete streams.
"""

from .streaming_json_parser import StreamingJSONParser, JSONParserHandler

__all__ = ['StreamingJSONParser', 'JSONParserHandler']
__version__ = '0.1.0'
