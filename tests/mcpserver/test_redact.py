from hyndsyght.mcpserver.redact import redact_title


def test_redacted_by_default() -> None:
    assert redact_title("secret document.pdf") is None


def test_none_title_stays_none_either_way() -> None:
    assert redact_title(None) is None
    assert redact_title(None, enabled=False) is None


def test_explicit_opt_out_returns_the_original() -> None:
    assert redact_title("secret document.pdf", enabled=False) == "secret document.pdf"
