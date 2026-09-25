from hyndsyght.agentwatch.intent import extract_intent


def test_missing_message_returns_none() -> None:
    assert extract_intent({}) is None


def test_blank_message_returns_none() -> None:
    assert extract_intent({"last_assistant_message": "   "}) is None


def test_extracts_first_sentence() -> None:
    payload = {"last_assistant_message": "Fixed the bug. Also ran the tests."}
    assert extract_intent(payload) == "Fixed the bug."


def test_message_without_terminal_punctuation_is_used_whole() -> None:
    payload = {"last_assistant_message": "Refactored the auth module"}
    assert extract_intent(payload) == "Refactored the auth module"


def test_long_first_sentence_is_bounded() -> None:
    payload = {"last_assistant_message": ("a" * 300) + ". done"}
    intent = extract_intent(payload)
    assert intent is not None
    assert len(intent) == 200
