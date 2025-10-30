"""
jaxn - A SAX-style JSON parser for incomplete streams.
"""

from .jaxn import StreamingJSONParser, JSONParserHandler

__all__ = ['StreamingJSONParser', 'JSONParserHandler']
__version__ = '0.1.0'
