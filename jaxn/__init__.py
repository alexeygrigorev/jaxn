"""
Streaming JSON Parser - A SAX-style JSON parser for incomplete streams.
"""

from .jaxn import StreamingJSONParser, JSONParserHandler
from .__version__ import __version__


__all__ = [
    'StreamingJSONParser',
    'JSONParserHandler',
    '__version__',
]
