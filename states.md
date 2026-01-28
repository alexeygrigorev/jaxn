# Parser State Machine

This document describes the state machine used by the streaming JSON parser.

Note: The parser uses a state machine pattern internally. For full implementation details, see [states.py](jaxn/states.py).

## State Diagram

```
stateDiagram-v2
    [*] --> Root

    Root --> InObjectWait : open brace {
    Root --> InArrayWait : open bracket [
    Root --> Root : whitespace

    InObjectWait --> FieldName : quote starts field name
    InObjectWait --> Root : close brace, empty object
    InObjectWait --> InObjectWait : comma before next field
    InObjectWait --> InObjectWait : whitespace

    FieldName --> Escape : backslash
    FieldName --> AfterFieldName : closing quote

    AfterFieldName --> AfterColon : colon
    AfterFieldName --> AfterFieldName : whitespace

    AfterColon --> ValueString : quote for string value
    AfterColon --> InObjectWait : open brace for object
    AfterColon --> InArrayWait : open bracket for array
    AfterColon --> Primitive : digit or true false null minus
    AfterColon --> AfterColon : whitespace

    ValueString --> Escape : backslash
    ValueString --> InObjectWait : closing quote in object
    ValueString --> InArrayWait : closing quote in array

    Primitive --> InObjectWait : comma in object
    Primitive --> InArrayWait : comma in array
    Primitive --> Root : close brace
    Primitive --> Root : close bracket

    InArrayWait --> ValueString : quote for string
    InArrayWait --> InObjectWait : open brace for object
    InArrayWait --> InArrayWait : nested array
    InArrayWait --> Primitive : digit or true false null minus
    InArrayWait --> Root : close bracket empty array
    InArrayWait --> InArrayWait : comma between items
    InArrayWait --> InArrayWait : whitespace

    Escape --> UnicodeEscape : letter u
    Escape --> FieldName : simple escape in field name
    Escape --> ValueString : simple escape in value

    UnicodeEscape --> FieldName : 4 hex digits complete
    UnicodeEscape --> ValueString : 4 hex digits complete
```

## State Descriptions

### RootState

[Purpose]: Initial state or between top-level values. [Source](jaxn/states.py#L160)

Transitions:
- `{` → InObjectWaitState - Start parsing a JSON object
- `[` → InArrayWaitState - Start parsing a JSON array
- Whitespace (space, tab, newline, carriage return) → Stay in RootState

### InObjectWaitState

[Purpose]: Inside an object, waiting for field name or end. [Source](jaxn/states.py#L348)

Transitions:
- `"` → FieldNameState - Start parsing a field name
- `}` → RootState - End of object (empty object or after last field)
- `,` → Stay in InObjectWaitState - Comma before next field
- Whitespace → Stay in InObjectWaitState

### FieldNameState

[Purpose]: Parsing a field name (before colon). [Source](jaxn/states.py#L180)

Transitions:
- `\` → EscapeState - Start of escape sequence
- `"` → AfterFieldNameState - End of field name

The field name characters are accumulated in the buffer. Escape sequences are decoded before the field name is stored.

### AfterFieldNameState

[Purpose]: Just finished field name, expecting colon. [Source](jaxn/states.py#L201)

Transitions:
- `:` → AfterColonState - Colon before value
- Whitespace → Stay in AfterFieldNameState

### AfterColonState

[Purpose]: Just saw colon, expecting value. [Source](jaxn/states.py#L214)

Transitions:
- `"` → ValueStringState - String value
- `{` → InObjectWaitState - Nested object value
- `[` → InArrayWaitState - Array value
- `0-9` or `t` or `f` or `n` or `-` → PrimitiveState - Primitive value (number, boolean, null)
- Whitespace → Stay in AfterColonState

### ValueStringState

[Purpose]: Inside a string value. [Source](jaxn/states.py#L259)

Transitions:
- `\` → EscapeState - Start of escape sequence
- `"` → InObjectWaitState - End of string value (in object)
- `"` → InArrayWaitState - End of string value (in array)
- Any other character → Stay in ValueStringState (adds to buffer and sends on_value_chunk callback)

### PrimitiveState

[Purpose]: Parsing a number, boolean, or null value. [Source](jaxn/states.py#L303)

Transitions:
- `,` → InObjectWaitState - Comma after primitive in object
- `,` → InArrayWaitState - Comma after primitive in array
- `}` → RootState - End of object after primitive value
- `]` → RootState - End of array after primitive value

Primitive values include: numbers (integers, floats, negative), true, false, null.

### InArrayWaitState

[Purpose]: Inside an array, waiting for value or end. [Source](jaxn/states.py#L369)

Transitions:
- `"` → ValueStringState - String array item
- `{` → InObjectWaitState - Object array item
- `[` → Stay in InArrayWaitState - Nested array (bracket pushed to stack)
- `0-9` or `t` or `f` or `n` or `-` → PrimitiveState - Primitive array item
- `]` → RootState - End of array
- `,` → Stay in InArrayWaitState - Comma between items
- Whitespace → Stay in InArrayWaitState

### EscapeState

[Purpose]: Processing escape sequence \X. [Source](jaxn/states.py#L422)

Transitions:
- `u` → UnicodeEscapeState - Unicode escape sequence \uXXXX
- Any other character → Back to previous state (FieldNameState or ValueStringState)

Simple escape sequences:
- `\n` → newline
- `\t` → tab
- `\r` → carriage return
- `\\` → backslash
- `\"` → quote
- `\/` → slash
- `\b` → backspace
- `\f` → form feed

### UnicodeEscapeState

[Purpose]: Processing unicode escape \uXXXX. [Source](jaxn/states.py#L473)

Transitions:
- After 4 hex digits → Back to previous state (FieldNameState or ValueStringState)

The 4 hex digits are accumulated and decoded to a Unicode character.

## Helper Functions

Several helper functions manage state transitions for complex scenarios:

### handle_close_brace(tracker, extractor, handler, parser)

[Source](jaxn/states.py#L18)

Handles closing `}` brace:
- Fires on_array_item_end if the object is inside an array
- Pops bracket stack and path stack
- Transitions to InArrayWaitState, InObjectWaitState, or RootState based on new stack top

### handle_close_bracket(tracker, extractor, handler, parser)

[Source](jaxn/states.py#L43)

Handles closing `]` bracket:
- Fires on_array_item_end for the last primitive item if applicable
- Fires on_field_end for the completed array
- Pops bracket stack and path stack
- Transitions to InArrayWaitState, InObjectWaitState, or RootState

### check_primitive_array_item_end(tracker, extractor, handler, last_char)

[Source](jaxn/states.py#L83)

Checks if a primitive item in an array just ended.
Fires on_array_item_end for the completed item.

### check_primitive_array_item_end_on_seperator(tracker, extractor, handler)

[Source](jaxn/states.py#L99)

Similar to above, but checks by looking backward from comma or `]` to find the last non-whitespace character.

## Tracker Helper Methods

The tracker class provides several helper methods for checking state:

- [at_array_level()](jaxn/tracker.py#L102) - Check if path_stack top is an array
- [at_object_level()](jaxn/tracker.py#L111) - Check if path_stack top is an object
- [has_brackets()](jaxn/tracker.py#L120) - Check if bracket stack is not empty
- [is_object_in_array()](jaxn/tracker.py#L124) - Check if we're an object directly inside an array
- [in_array()](jaxn/tracker.py#L94) - Check if bracket_stack top is '['
- [in_object()](jaxn/tracker.py#L98) - Check if bracket_stack top is '{'

## State References

Each state maintains references to:
- parser - The parent parser
- tracker - Manages bracket stack, path stack, context buffer (see [tracker.py](jaxn/tracker.py))
- handler - Callback interface (see [handler.py](jaxn/handler.py))
- buffers - Buffer manager for field names, strings, unicode sequences (see [buffers.py](jaxn/buffers.py))

## Example Parsing Flow

For JSON: `{"name": "value"}`

```
Root --'{'--> InObjectWait
InObjectWait --'"'--> FieldName
FieldName --'n','a','m','e'--> FieldName (accumulating)
FieldName --'"'--> AfterFieldName (field_name = "name")
AfterFieldName --':'--> AfterColon
AfterColon --'"'--> ValueString
ValueString --'v','a','l','u','e'--> ValueString (accumulating + chunks)
ValueString --'"'--> InObjectWait
InObjectWait --'}'--> Root
```

## Notes

- Whitespace handling: Most states ignore whitespace without transitioning
- Nested structures: Bracket stack tracks nesting depth for `{` and `[`
- Path tracking: Path stack builds JSONPath-like strings for callbacks
- Callbacks: State transitions trigger appropriate handler callbacks (on_field_start, on_field_end, on_array_item_start, on_array_item_end, on_value_chunk)
- Context buffer: All parsed characters are stored for value extraction

For the complete state machine implementation with all 10 states, see [states.py](jaxn/states.py).
