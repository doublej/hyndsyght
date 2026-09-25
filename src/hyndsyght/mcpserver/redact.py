"""Title redaction — on by default, applied inside each tool function itself,
before a row ever leaves Python. Never a separate pass a caller could dodge.
"""


def redact_title(title: str | None, *, enabled: bool = True) -> str | None:
    if not enabled or title is None:
        return title
    return None
