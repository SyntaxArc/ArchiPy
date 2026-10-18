"""Persian digit type enumeration and its English-to-Persian translate table."""

from enum import StrEnum


class PersianDigitType(StrEnum):
    """Enum of the Persian digits and the Persian comma, in the order of ``0-9`` and ``,``.

    Attributes:
        ZERO .. NINE (str): The Persian digits ``۰`` to ``۹`` (U+06F0 to U+06F9).
        COMMA (str): The Persian comma ``،`` (U+060C).
    """

    ZERO = "۰"
    ONE = "۱"
    TWO = "۲"
    THREE = "۳"
    FOUR = "۴"
    FIVE = "۵"
    SIX = "۶"
    SEVEN = "۷"
    EIGHT = "۸"
    NINE = "۹"
    COMMA = "،"


ENGLISH_TO_PERSIAN_DIGITS_TABLE: dict[int, str] = str.maketrans(
    dict(zip("0123456789,", (digit.value for digit in PersianDigitType), strict=True)),
)
"""Translate table for ``str.translate`` that turns English digits and ``,`` into their Persian forms."""
