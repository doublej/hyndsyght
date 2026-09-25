"""Pre-write redact/away checks — a miss on redact is a permanent privacy leak, so it fails closed."""

from hyndsyght.categorize.rules import Rules


def should_redact(title: str | None, rules: Rules) -> bool:
    if not title:
        return False
    return any(pattern.search(title) for pattern in rules.redact_patterns)


def is_away(title: str | None, rules: Rules) -> bool:
    if not title:
        return False
    return any(pattern.search(title) for pattern in rules.away_patterns)
