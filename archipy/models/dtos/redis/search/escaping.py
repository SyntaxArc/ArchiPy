"""Escaping and validation helpers for RediSearch query construction."""

import re
from typing import Annotated

from pydantic import StringConstraints

__all__ = ["SearchIdentifier", "escape_tag", "escape_text", "quote_phrase"]

_SPECIAL_CHARS = re.compile(r"""([,.<>{}\[\]"':;!@#$%^&*()\-+=~|/\\?\s])""")

SearchIdentifier = Annotated[str, StringConstraints(pattern=r"^@?[A-Za-z_$][A-Za-z0-9_.$\-]*$", max_length=256)]
"""A field or alias name: letters, digits, ``_``, ``.``, ``$`` and ``-`` only, with an optional leading ``@``."""


def escape_text(value: str) -> str:
    """Escape every RediSearch punctuation and whitespace character so ``value`` is one literal term.

    Args:
        value (str): Untrusted text for a full-text or tag clause.

    Returns:
        str: The value with each special character prefixed by a backslash.
    """
    return _SPECIAL_CHARS.sub(r"\\\1", value)


def escape_tag(value: str) -> str:
    """Escape a value for use inside a tag clause such as ``@tags:{value}``.

    Args:
        value (str): Untrusted tag value.

    Returns:
        str: The escaped tag value.
    """
    return escape_text(value)


def quote_phrase(value: str) -> str:
    """Quote ``value`` as an exact-phrase clause, escaping backslashes and quotes.

    Args:
        value (str): Untrusted phrase.

    Returns:
        str: The phrase wrapped in double quotes.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
