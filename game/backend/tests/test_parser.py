"""Tests for parse_command()."""

from __future__ import annotations

from game.parser import UNKNOWN_VERB_MSG, parse_command


class TestParseCommandBasics:
    def test_empty_input_is_unknown(self):
        assert parse_command("").verb == "unknown"
        assert parse_command("   ").verb == "unknown"

    def test_inventory_aliases(self):
        for cmd in ("inventory", "inv", "i"):
            assert parse_command(cmd).verb == "inventory"

    def test_look_around(self):
        assert parse_command("look around").verb == "look"

    def test_unknown_verb(self):
        parsed = parse_command("dance wildly")
        assert parsed.verb == "unknown"


class TestParseGo:
    def test_go_direction_short(self):
        parsed = parse_command("go n")
        assert parsed.verb == "go"
        assert parsed.direction == "n"

    def test_go_direction_compound(self):
        parsed = parse_command("walk north-west")
        assert parsed.verb == "go"
        assert parsed.direction == "north-west"

    def test_go_object_target(self):
        parsed = parse_command("go door")
        assert parsed.verb == "go"
        assert parsed.target == "door"
        assert parsed.direction is None


class TestParseUseOpen:
    def test_use_with_secondary(self):
        parsed = parse_command("use small key with lockbox")
        assert parsed.verb == "use"
        assert parsed.target == "small key"
        assert parsed.secondary == "lockbox"

    def test_use_code_digits(self):
        parsed = parse_command("use safe 617482")
        assert parsed.verb == "use"
        assert parsed.target == "safe"
        assert parsed.secondary == "617482"

    def test_open_with_key(self):
        parsed = parse_command("unlock door with brass key")
        assert parsed.verb == "open"
        assert parsed.target == "door"
        assert parsed.secondary == "brass key"


class TestParseExamineTake:
    def test_examine_aliases(self):
        parsed = parse_command("look at lockbox")
        assert parsed.verb == "examine"
        assert parsed.target == "lockbox"

    def test_take_aliases(self):
        parsed = parse_command("pick up brass key")
        assert parsed.verb == "take"
        assert parsed.target == "brass key"


class TestParseOptionalTargetVerbs:
    def test_read_without_target(self):
        assert parse_command("read").verb == "read"
        assert parse_command("read").target is None

    def test_read_with_target(self):
        parsed = parse_command("read memo")
        assert parsed.verb == "read"
        assert parsed.target == "memo"

    def test_touch_pull_speak(self):
        assert parse_command("touch").target is None
        assert parse_command("pull painting").target == "painting"
        assert parse_command("speak to grate").target == "grate"


class TestUnknownVerbMessage:
    def test_message_documents_available_verbs(self):
        assert "examine" in UNKNOWN_VERB_MSG
        assert "read" in UNKNOWN_VERB_MSG
        assert "touch" in UNKNOWN_VERB_MSG
        assert "use x with y" in UNKNOWN_VERB_MSG
