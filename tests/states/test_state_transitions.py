"""
State Transition Tests - Verify parser state machine transitions.

Tests that the parser correctly transitions between states for various
JSON patterns.
"""

import pytest
from jaxn.parser import StreamingJSONParser
from jaxn.handler import JSONParserHandler
from jaxn.states import (
    RootState,
    FieldNameState,
    AfterFieldNameState,
    AfterColonState,
    ValueStringState,
    PrimitiveState,
    InObjectWaitState,
    InArrayWaitState,
    EscapeState,
    UnicodeEscapeState,
    ParserState,
)


class CaptureHandler(JSONParserHandler):
    """Test handler to capture callbacks."""

    def __init__(self):
        self.calls = []

    def on_field_start(self, path, field_name):
        self.calls.append(('field_start', path, field_name))

    def on_field_end(self, path, field_name, raw_value, parsed_value=None):
        self.calls.append(('field_end', path, field_name, raw_value, parsed_value))

    def on_array_item_start(self, path, field_name):
        self.calls.append(('array_item_start', path, field_name))

    def on_array_item_end(self, path, field_name, item=None):
        self.calls.append(('array_item_end', path, field_name, item))

    def on_value_chunk(self, path, field_name, chunk):
        self.calls.append(('value_chunk', path, field_name, chunk))


class TestRootStateTransitions:
    """Test transitions from RootState."""

    def test_root_to_object_on_open_brace(self):
        """RootState transitions to InObjectWaitState on '{'."""
        parser = StreamingJSONParser()
        assert isinstance(parser.state, RootState)

        parser.parse_incremental('{')


        assert isinstance(parser.state, InObjectWaitState)
        assert parser.tracker.bracket_stack == ['{']

    def test_root_to_array_on_open_bracket(self):
        """RootState transitions to InArrayWaitState on '['."""
        parser = StreamingJSONParser()
        assert isinstance(parser.state, RootState)

        parser.parse_incremental('[')

        assert isinstance(parser.state, InArrayWaitState)
        assert parser.tracker.bracket_stack == ['[']

    def test_root_ignores_whitespace(self):
        """RootState ignores whitespace before value."""
        parser = StreamingJSONParser()
        assert isinstance(parser.state, RootState)

        parser.parse_incremental('   \t\n')

        assert isinstance(parser.state, RootState)


class TestInObjectWaitStateTransitions:
    """Test transitions from InObjectWaitState."""

    def test_object_wait_to_field_name_on_quote(self):
        """InObjectWaitState transitions to FieldNameState on '"'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"')  # RootState -> InObjectWaitState -> FieldNameState

        assert isinstance(parser.state, FieldNameState)

    def test_object_wait_to_root_on_close_brace(self):
        """InObjectWaitState transitions to RootState on '}' for empty object."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{}')

        assert isinstance(parser.state, RootState)
        assert parser.tracker.bracket_stack == []

    def test_object_wait_stays_on_comma(self):
        """InObjectWaitState handles comma (ready for next field)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":1,')  # After first field, on comma

        assert isinstance(parser.state, InObjectWaitState)

    def test_object_wait_ignores_whitespace(self):
        """InObjectWaitState ignores whitespace."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{  ')

        assert isinstance(parser.state, InObjectWaitState)


class TestFieldNameStateTransitions:
    """Test transitions from FieldNameState."""

    def test_field_name_to_after_field_name_on_quote(self):
        """FieldNameState transitions to AfterFieldNameState on closing quote."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"name"')

        assert isinstance(parser.state, AfterFieldNameState)
        assert parser.tracker.field_name == "name"

    def test_field_name_handles_escape_sequences(self):
        r"""FieldNameState processes unicode escape sequences.

        The \u0063 escape sequence (hex for 'c') is decoded to the letter 'c'.
        """
        parser = StreamingJSONParser()
        parser.parse_incremental('{"na\\u0063me"')  # unicode escape for 'c'

        assert isinstance(parser.state, AfterFieldNameState)
        # Unicode escapes in field names ARE decoded (unlike what I thought)
        assert parser.tracker.field_name == "nacme"

    def test_field_name_handles_simple_escape(self):
        """FieldNameState processes simple escape sequences."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"na\\nme"')

        assert isinstance(parser.state, AfterFieldNameState)
        assert parser.tracker.field_name == "na\nme"

    def test_field_name_escape_state_transition(self):
        """FieldNameState transitions to EscapeState on backslash."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a\\')  # In middle of escape

        assert isinstance(parser.state, EscapeState)


class TestAfterFieldNameStateTransitions:
    """Test transitions from AfterFieldNameState."""

    def test_after_field_name_to_after_colon_on_colon(self):
        """AfterFieldNameState transitions to AfterColonState on ':'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":')

        assert isinstance(parser.state, AfterColonState)

    def test_after_field_name_ignores_whitespace_before_colon(self):
        """AfterFieldNameState ignores whitespace before colon."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a"   :')

        assert isinstance(parser.state, AfterColonState)


class TestAfterColonStateTransitions:
    """Test transitions from AfterColonState."""

    def test_after_colon_to_string_state_on_quote(self):
        """AfterColonState transitions to ValueStringState on '"'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"')

        assert isinstance(parser.state, ValueStringState)

    def test_after_colon_to_object_wait_on_open_brace(self):
        """AfterColonState transitions to InObjectWaitState on '{'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":{')

        assert isinstance(parser.state, InObjectWaitState)

    def test_after_colon_to_array_wait_on_open_bracket(self):
        """AfterColonState transitions to InArrayWaitState on '['."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":[')

        assert isinstance(parser.state, InArrayWaitState)

    def test_after_colon_to_primitive_state_on_digit(self):
        """AfterColonState transitions to PrimitiveState on digit."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":4')

        assert isinstance(parser.state, PrimitiveState)

    def test_after_colon_to_primitive_state_on_true(self):
        """AfterColonState transitions to PrimitiveState on 't' (true)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":t')

        assert isinstance(parser.state, PrimitiveState)

    def test_after_colon_to_primitive_state_on_false(self):
        """AfterColonState transitions to PrimitiveState on 'f' (false)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":f')

        assert isinstance(parser.state, PrimitiveState)

    def test_after_colon_to_primitive_state_on_null(self):
        """AfterColonState transitions to PrimitiveState on 'n' (null)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":n')

        assert isinstance(parser.state, PrimitiveState)

    def test_after_colon_to_primitive_state_on_minus(self):
        """AfterColonState transitions to PrimitiveState on '-' (negative number)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":-')

        assert isinstance(parser.state, PrimitiveState)

    def test_after_colon_ignores_whitespace(self):
        """AfterColonState ignores whitespace before value."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":   ')

        assert isinstance(parser.state, AfterColonState)


class TestValueStringStateTransitions:
    """Test transitions from ValueStringState."""

    def test_string_to_object_wait_on_close_quote(self):
        """ValueStringState transitions to InObjectWaitState on closing quote."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"value"')

        assert isinstance(parser.state, InObjectWaitState)

    def test_string_in_array_to_array_wait_on_close_quote(self):
        """ValueStringState transitions to InArrayWaitState when in array."""
        parser = StreamingJSONParser()
        parser.parse_incremental('["value"')

        assert isinstance(parser.state, InArrayWaitState)

    def test_string_to_escape_state_on_backslash(self):
        """ValueStringState transitions to EscapeState on backslash."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"val\\')

        assert isinstance(parser.state, EscapeState)

    def test_string_sends_value_chunks(self):
        """ValueStringState sends value chunks to handler."""
        handler = CaptureHandler()
        parser = StreamingJSONParser(handler)
        parser.parse_incremental('{"a":"hello"}')

        chunks = [c for c in handler.calls if c[0] == 'value_chunk']
        assert len(chunks) == 5
        # Path is empty during chunking because field isn't added to path yet
        # The field name is passed separately
        assert chunks[0] == ('value_chunk', '', 'a', 'h')
        assert chunks[1] == ('value_chunk', '', 'a', 'e')
        assert chunks[2] == ('value_chunk', '', 'a', 'l')
        assert chunks[3] == ('value_chunk', '', 'a', 'l')
        assert chunks[4] == ('value_chunk', '', 'a', 'o')


class TestPrimitiveStateTransitions:
    """Test transitions from PrimitiveState."""

    def test_primitive_to_object_wait_on_comma(self):
        """PrimitiveState transitions to InObjectWaitState on comma."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":42,')

        assert isinstance(parser.state, InObjectWaitState)

    def test_primitive_to_array_wait_on_comma_in_array(self):
        """PrimitiveState transitions to InArrayWaitState on comma in array."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[42,')

        assert isinstance(parser.state, InArrayWaitState)

    def test_primitive_to_root_on_close_brace(self):
        """PrimitiveState transitions to RootState on '}'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":42}')

        assert isinstance(parser.state, RootState)

    def test_primitive_to_root_on_close_bracket(self):
        """PrimitiveState transitions to RootState on ']'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[42]')

        assert isinstance(parser.state, RootState)

    def test_primitive_accumulates_digits(self):
        """PrimitiveState accumulates multi-digit numbers."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":12345}')

        assert isinstance(parser.state, RootState)


class TestInArrayWaitStateTransitions:
    """Test transitions from InArrayWaitState."""

    def test_array_wait_to_string_on_quote(self):
        """InArrayWaitState transitions to ValueStringState on '"'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('["')

        assert isinstance(parser.state, ValueStringState)

    def test_array_wait_to_object_wait_on_open_brace(self):
        """InArrayWaitState transitions to InObjectWaitState on '{'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[{')

        assert isinstance(parser.state, InObjectWaitState)

    def test_array_wait_to_nested_array_on_open_bracket(self):
        """InArrayWaitState stays in InArrayWaitState on '[' (nested array)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[[')

        assert isinstance(parser.state, InArrayWaitState)
        assert len(parser.tracker.bracket_stack) == 2

    def test_array_wait_to_primitive_on_digit(self):
        """InArrayWaitState transitions to PrimitiveState on digit."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[4')

        assert isinstance(parser.state, PrimitiveState)

    def test_array_wait_to_primitive_on_true(self):
        """InArrayWaitState transitions to PrimitiveState on 't' (true)."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[t')

        assert isinstance(parser.state, PrimitiveState)

    def test_array_wait_to_root_on_close_bracket(self):
        """InArrayWaitState transitions to RootState on ']'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[]')

        assert isinstance(parser.state, RootState)

    def test_array_wait_handles_comma(self):
        """InArrayWaitState handles comma between items."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[1,')

        assert isinstance(parser.state, InArrayWaitState)

    def test_array_wait_ignores_whitespace(self):
        """InArrayWaitState ignores whitespace."""
        parser = StreamingJSONParser()
        parser.parse_incremental('[   ')

        assert isinstance(parser.state, InArrayWaitState)


class TestEscapeStateTransitions:
    """Test transitions from EscapeState."""

    def test_escape_back_to_string_on_simple_escape(self):
        """EscapeState transitions back to ValueStringState after simple escape."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"\\n"')

        assert isinstance(parser.state, InObjectWaitState)

    def test_escape_to_unicode_state_on_u(self):
        """EscapeState transitions to UnicodeEscapeState on 'u'."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"\\u')

        assert isinstance(parser.state, UnicodeEscapeState)

    def test_escape_back_to_field_name(self):
        """EscapeState transitions back to FieldNameState when escaping field name."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a\\n":')

        assert isinstance(parser.state, AfterColonState)

    def test_escape_handles_all_simple_escapes(self):
        """EscapeState handles all simple escape sequences."""
        escapes = ['\\n', '\\t', '\\r', '\\\\', '\\"', '\\/', '\\b', '\\f']

        for esc in escapes:
            parser = StreamingJSONParser()
            parser.parse_incremental(f'{{"a":"{esc}"}}')
            assert isinstance(parser.state, RootState)


class TestUnicodeEscapeStateTransitions:
    """Test transitions from UnicodeEscapeState."""

    def test_unicode_escape_back_to_string(self):
        """UnicodeEscapeState transitions back to ValueStringState after 4 hex digits."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"\\u0041"}')  # 'A'

        assert isinstance(parser.state, RootState)

    def test_unicode_escape_back_to_field_name(self):
        """UnicodeEscapeState transitions back to FieldNameState after 4 hex digits."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"\\u0061":')  # 'a'

        assert isinstance(parser.state, AfterColonState)

    def test_unicode_escape_stays_until_4_digits(self):
        """UnicodeEscapeState stays until 4 hex digits are received."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"\\u00')

        assert isinstance(parser.state, UnicodeEscapeState)

    def test_unicode_escape_handles_various_chars(self):
        """UnicodeEscapeState handles various hex values."""
        test_cases = [
            '\\u0041',  # A
            '\\u007A',  # z
            '\\u4E2D',  # 中 (CJK character)
        ]

        for esc in test_cases:
            parser = StreamingJSONParser()
            parser.parse_incremental(f'{{"a":"{esc}"}}')
            assert isinstance(parser.state, RootState)


class TestComplexStateTransitions:
    """Test complex multi-state transitions."""

    def test_nested_object_state_transitions(self):
        """Test state transitions through nested objects."""
        parser = StreamingJSONParser()
        json_str = '{"a":{"b":{"c":1}}}'

        for char in json_str:
            old_state = type(parser.state).__name__
            parser.parse_incremental(char)
            # Each character should result in a valid state

        assert isinstance(parser.state, RootState)

    def test_nested_array_state_transitions(self):
        """Test state transitions through nested arrays."""
        parser = StreamingJSONParser()
        json_str = '[[[1]]]'

        for char in json_str:
            parser.parse_incremental(char)

        assert isinstance(parser.state, RootState)

    def test_mixed_nesting_state_transitions(self):
        """Test state transitions through mixed array/object nesting."""
        parser = StreamingJSONParser()
        json_str = '{"a":[{"b":[1,2,3]}]}'

        for char in json_str:
            parser.parse_incremental(char)

        assert isinstance(parser.state, RootState)

    def test_state_chain_for_simple_string_value(self):
        """Verify full state chain for simple string value."""
        parser = StreamingJSONParser()

        # { -> InObjectWaitState
        parser.parse_incremental('{')
        assert isinstance(parser.state, InObjectWaitState)

        # " -> FieldNameState
        parser.parse_incremental('"')
        assert isinstance(parser.state, FieldNameState)

        # key" -> AfterFieldNameState
        parser.parse_incremental('key"')
        assert isinstance(parser.state, AfterFieldNameState)

        # : -> AfterColonState
        parser.parse_incremental(':')
        assert isinstance(parser.state, AfterColonState)

        # " -> ValueStringState
        parser.parse_incremental('"')
        assert isinstance(parser.state, ValueStringState)

        # value" -> InObjectWaitState
        parser.parse_incremental('value"')
        assert isinstance(parser.state, InObjectWaitState)

        # } -> RootState
        parser.parse_incremental('}')
        assert isinstance(parser.state, RootState)

    def test_state_chain_for_array_of_numbers(self):
        """Verify full state chain for array of numbers."""
        parser = StreamingJSONParser()

        # [ -> InArrayWaitState
        parser.parse_incremental('[')
        assert isinstance(parser.state, InArrayWaitState)

        # 1 -> PrimitiveState
        parser.parse_incremental('1')
        assert isinstance(parser.state, PrimitiveState)

        # , -> InArrayWaitState
        parser.parse_incremental(',')
        assert isinstance(parser.state, InArrayWaitState)

        # 2 -> PrimitiveState
        parser.parse_incremental('2')
        assert isinstance(parser.state, PrimitiveState)

        # ] -> RootState
        parser.parse_incremental(']')
        assert isinstance(parser.state, RootState)

    def test_previous_state_tracking(self):
        """Test that _previous_state is properly maintained."""
        parser = StreamingJSONParser()

        parser.parse_incremental('{"a":')

        # After transitioning from AfterColonState to ValueStringState
        # the previous state should be AfterColonState
        parser.parse_incremental('"')
        assert isinstance(parser._previous_state, AfterColonState)

        # After processing character, previous state becomes EscapeState
        # and current becomes ValueStringState again
        parser.parse_incremental('\\')
        assert isinstance(parser.state, EscapeState)
        assert isinstance(parser._previous_state, ValueStringState)


class TestStateProperties:
    """Test state properties and attributes."""

    def test_states_have_parser_reference(self):
        """All states have reference to parser."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"key": "value"}')

        # State should have been replaced during parsing
        # but original RootState should have parser
        root_state = RootState(parser)
        assert root_state.parser is parser
        assert root_state.tracker is parser.tracker
        assert root_state.handler is parser.handler
        assert root_state.buffers is parser.buffers

    def test_states_have_tracker_reference(self):
        """States have direct reference to tracker."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{')

        assert isinstance(parser.state, InObjectWaitState)
        assert parser.state.tracker is parser.tracker

    def test_states_have_handler_reference(self):
        """States have direct reference to handler."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{')

        assert isinstance(parser.state, InObjectWaitState)
        assert parser.state.handler is parser.handler

    def test_states_have_buffers_reference(self):
        """States have direct reference to buffers."""
        parser = StreamingJSONParser()
        parser.parse_incremental('{"a":"' )

        assert isinstance(parser.state, ValueStringState)
        assert parser.state.buffers is parser.buffers


class TestEdgeCaseTransitions:
    """Test edge case state transitions."""

    def test_empty_object_transitions(self):
        """Test state transitions for empty object {}."""
        parser = StreamingJSONParser()

        parser.parse_incremental('{')
        assert isinstance(parser.state, InObjectWaitState)

        parser.parse_incremental('}')
        assert isinstance(parser.state, RootState)

    def test_empty_array_transitions(self):
        """Test state transitions for empty array []."""
        parser = StreamingJSONParser()

        parser.parse_incremental('[')
        assert isinstance(parser.state, InArrayWaitState)

        parser.parse_incremental(']')
        assert isinstance(parser.state, RootState)

    def test_whitespace_only_root(self):
        """Test that RootState handles only whitespace."""
        parser = StreamingJSONParser()
        parser.parse_incremental('   \t\n   ')

        assert isinstance(parser.state, RootState)

    def test_multiple_objects_sequence(self):
        """Test parsing multiple objects in sequence."""
        parser = StreamingJSONParser()
        handler = CaptureHandler()
        parser.handler = handler

        parser.parse_incremental('{"a":1}')
        assert isinstance(parser.state, RootState)

        parser.parse_incremental('{"b":2}')
        assert isinstance(parser.state, RootState)

        field_ends = [c for c in handler.calls if c[0] == 'field_end']
        assert len(field_ends) == 2

    def test_consecutive_commas_in_array(self):
        """Test that parser handles consecutive commas (invalid but shouldn't crash)."""
        parser = StreamingJSONParser()
        # This is invalid JSON but parser shouldn't crash
        parser.parse_incremental('[1,,2]')
        # Just verify we end in a valid state
        assert isinstance(parser.state, RootState)
