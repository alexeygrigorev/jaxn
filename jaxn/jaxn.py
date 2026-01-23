"""
Generic SAX-style JSON parser that processes incomplete JSON streams.
Similar to XML SAX parsers, this processes JSON character-by-character and 
triggers callbacks without building a full DOM tree.
"""

import json as json_module
from typing import Dict, Any


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
    
    def on_array_item_end(self, path: str, field_name: str, item: Dict[str, Any] = None) -> None:
        """
        Called when finishing an object in an array.
        
        Args:
            path: Path to current location (e.g., "/sections/references")
            field_name: Name of the array field
            item: The complete parsed dictionary for this array item
        """
        pass


class StreamingJSONParser:
    """
    Parse JSON incrementally as it streams in, character by character.
    Fires callbacks when fields are detected, without requiring complete JSON.
    """
    
    def __init__(self, handler: JSONParserHandler = None):
        """
        Initialize the parser with a handler for events.
        
        Args:
            handler: JSONParserHandler instance to receive parsing events
        """
        self.handler = handler or JSONParserHandler()
        self.in_value = False
        self.in_field_name = False
        self.current_field = None
        self.escape_next = False
        self.after_colon = False
        self.recent_context = ""  # Keep recent JSON for context detection - also used for parsing complete values
        self.buffer = ""  # Accumulation buffer for current string
        self.path_stack = []  # Stack of (field_name, bracket_type): e.g., [('sections', '['), ('references', '[')]
        self.bracket_stack = []  # Stack of just bracket types: e.g., ['{', '[', '{']
        self.pending_escape = ""  # Store backslash when we see it, to decode with next char
        self.object_start_pos = {}  # Track start position in recent_context for each object: {(path, field): position}
        self.unicode_escape_buffer = ""  # Buffer for accumulating \uXXXX escape sequences
        self.in_unicode_escape = False  # Track if we're currently reading a \uXXXX sequence
        
    def parse_incremental(self, delta):
        """
        Parse new characters added since last call.
        Fires callbacks as events are detected.
        
        Args:
            delta: New characters to parse (string)
        """
        if not delta:
            return
        
        for char in delta:
            # Add to context (keep last 50000 chars for lookback - enough for large nested objects)
            self.recent_context += char
            if len(self.recent_context) > 50000:
                self.recent_context = self.recent_context[-50000:]
            
            # Handle unicode escape sequence continuation (\uXXXX)
            if self.in_unicode_escape:
                if self.in_value:
                    self.buffer += char
                    self.unicode_escape_buffer += char
                    
                    # We need 4 hex digits after \u
                    if len(self.unicode_escape_buffer) == 4:
                        # Try to decode the unicode escape
                        try:
                            code_point = int(self.unicode_escape_buffer, 16)
                            decoded_char = chr(code_point)
                            
                            # Send decoded character to handler
                            path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                            self.handler.on_value_chunk(path, self.current_field, decoded_char)
                        except (ValueError, OverflowError):
                            # Invalid unicode escape - send the literal characters including backslash
                            path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                            for ch in ('\\u' + self.unicode_escape_buffer):
                                self.handler.on_value_chunk(path, self.current_field, ch)
                        
                        # Reset unicode escape state
                        self.in_unicode_escape = False
                        self.unicode_escape_buffer = ""
                elif self.in_field_name:
                    # For field names, just accumulate in buffer - it will be parsed later
                    self.buffer += char
                    self.unicode_escape_buffer += char
                    
                    if len(self.unicode_escape_buffer) == 4:
                        # Reset state
                        self.in_unicode_escape = False
                        self.unicode_escape_buffer = ""
                else:
                    # Not in a string, shouldn't happen
                    self.in_unicode_escape = False
                    self.unicode_escape_buffer = ""
                continue
            
            # Handle escape sequences
            if self.escape_next:
                if self.in_value:
                    # Add escaped character to buffer (keep as-is for now)
                    self.buffer += char
                    
                    # Decode the escape sequence for streaming callback
                    if char == 'n':
                        decoded_char = '\n'
                    elif char == 't':
                        decoded_char = '\t'
                    elif char == 'r':
                        decoded_char = '\r'
                    elif char == '\\':
                        decoded_char = '\\'
                    elif char == '"':
                        decoded_char = '"'
                    elif char == '/':
                        decoded_char = '/'
                    elif char == 'u':
                        # Start of unicode escape sequence \uXXXX
                        self.in_unicode_escape = True
                        self.unicode_escape_buffer = ""
                        self.escape_next = False
                        continue
                    elif char == 'b':
                        decoded_char = '\b'
                    elif char == 'f':
                        decoded_char = '\f'
                    else:
                        # Unknown escape - keep as-is
                        decoded_char = char
                    
                    # Send decoded character to handler
                    path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                    self.handler.on_value_chunk(path, self.current_field, decoded_char)
                elif self.in_field_name:
                    # Handle escapes in field names too
                    self.buffer += char
                    if char == 'u':
                        # Start of unicode escape in field name
                        self.in_unicode_escape = True
                        self.unicode_escape_buffer = ""
                        self.escape_next = False
                        continue
                self.escape_next = False
                continue
            
            if char == '\\':
                self.escape_next = True
                if self.in_value:
                    self.buffer += char
                    # Don't send backslash to handler yet - wait for next char
                elif self.in_field_name:
                    self.buffer += char
                continue
            
            # Entering a string (either field name or value)
            if char == '"' and not self.in_value and not self.in_field_name:
                if self.after_colon:
                    # This is a value string - fire field start event
                    self.in_value = True
                    self.after_colon = False
                    path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                    self.handler.on_field_start(path, self.current_field)
                    self.buffer = ""
                else:
                    # This is a field name
                    self.in_field_name = True
                    self.buffer = ""
            
            # Exiting a string
            elif char == '"':
                if self.in_field_name:
                    # Finished reading field name
                    # Parse the field name to handle any escape sequences
                    try:
                        parsed_field_name = json_module.loads('"' + self.buffer + '"')
                        self.current_field = parsed_field_name
                    except Exception:
                        # If parsing fails, use the raw buffer
                        self.current_field = self.buffer
                    self.in_field_name = False
                    self.buffer = ""
                elif self.in_value:
                    # Finished reading value - fire field end event
                    field_name = self.current_field  # Save before clearing
                    # Build path string for the handler
                    path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                    # Parse the string value to handle escape sequences
                    try:
                        parsed_value = json_module.loads('"' + self.buffer + '"')
                    except Exception:
                        # If parsing fails, use the raw buffer
                        parsed_value = self.buffer
                    self.handler.on_field_end(path, field_name, self.buffer, parsed_value=parsed_value)
                    self.in_value = False
                    self.current_field = None
                    self.buffer = ""
            
            # Track colons (they come after field names, before values)
            elif char == ':' and not self.in_value and not self.in_field_name:
                self.after_colon = True
            
            # Handle non-string values (objects, arrays, booleans, numbers, null)
            elif (char in '{[' or char.isdigit() or char in 'tfn') and self.after_colon:
                # Non-string value - push field name onto stack for objects/arrays
                if char in '{[' and self.current_field:
                    # Fire field_start for array/object fields
                    path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                    self.handler.on_field_start(path, self.current_field)
                    
                    self.path_stack.append((self.current_field, char))
                    self.bracket_stack.append(char)
                self.after_colon = False
                self.current_field = None
            
            # Track root-level object/array opening
            elif char in '{[' and not self.in_value and not self.in_field_name and not self.after_colon:
                self.bracket_stack.append(char)
                
                # If opening { inside an array, fire array item start
                if char == '{' and self.bracket_stack and len(self.bracket_stack) >= 2 and self.bracket_stack[-2] == '[':
                    # We're starting an object inside an array
                    if self.path_stack and self.path_stack[-1][1] == '[':
                        array_field = self.path_stack[-1][0]
                        path = '/' + '/'.join([name for name, bracket in self.path_stack[:-1]]) if len(self.path_stack) > 1 else ''
                        self.handler.on_array_item_start(path, array_field)
            
            # Track closing of objects/arrays
            elif char in '}]' and not self.in_value and not self.in_field_name:
                # Determine what we're closing
                expected_opener = '{' if char == '}' else '['
                
                # If closing } inside an array, fire array item end
                if char == '}' and self.bracket_stack and len(self.bracket_stack) >= 2:
                    # Check if we're closing an object that's inside an array
                    if self.bracket_stack[-1] == '{' and self.bracket_stack[-2] == '[':
                        # We're ending an object inside an array
                        if self.path_stack and self.path_stack[-1][1] == '[':
                            array_field = self.path_stack[-1][0]
                            path = '/' + '/'.join([name for name, bracket in self.path_stack[:-1]]) if len(self.path_stack) > 1 else ''
                            # Extract and parse the complete object
                            parsed_obj = self._extract_last_complete_object()
                            self.handler.on_array_item_end(path, array_field, item=parsed_obj)
                
                # Pop from bracket stack
                if self.bracket_stack and self.bracket_stack[-1] == expected_opener:
                    self.bracket_stack.pop()
                    
                    # Also pop from path stack if this matches
                    if self.path_stack and self.path_stack[-1][1] == expected_opener:
                        self.path_stack.pop()
            
            # Accumulate content if we're inside a value
            elif self.in_value:
                # Store raw character in buffer
                self.buffer += char
                # Send to handler for streaming (escape handling is done above)
                path = '/' + '/'.join([name for name, bracket in self.path_stack]) if self.path_stack else ''
                self.handler.on_value_chunk(path, self.current_field, char)
            elif self.in_field_name:
                self.buffer += char
    
    def _extract_last_complete_object(self):
        """
        Extract the last complete JSON object from recent_context.
        Returns the parsed dict or None if extraction fails.
        """
        # Search backwards for the last complete {...} object
        bracket_count = 0
        start_pos = -1
        
        for i in range(len(self.recent_context) - 1, -1, -1):
            ch = self.recent_context[i]
            if ch == '}':
                bracket_count += 1
            elif ch == '{':
                bracket_count -= 1
                if bracket_count == 0:
                    start_pos = i
                    break
        
        if start_pos >= 0:
            json_str = self.recent_context[start_pos:]
            # Try to find where this object ends
            bracket_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(self.recent_context)):
                ch = self.recent_context[i]
                if ch == '{':
                    bracket_count += 1
                elif ch == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_pos = i + 1
                        break
            
            json_str = self.recent_context[start_pos:end_pos]
            try:
                return json_module.loads(json_str)
            except Exception:
                return None
        return None
    
    def parse_from_old_new(self, old_text, new_text):
        """
        Convenience method that calculates the delta between old and new text.
        
        Args:
            old_text: Previously processed text
            new_text: New text (should start with old_text)
        """
        if not new_text.startswith(old_text):
            raise ValueError("new_text must start with old_text")
        
        delta = new_text[len(old_text):]
        self.parse_incremental(delta)
