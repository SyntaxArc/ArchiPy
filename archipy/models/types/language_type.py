from enum import StrEnum


class LanguageType(StrEnum):
    """Enum representing supported languages for error messages.

    This enum defines the languages that are supported for generating or displaying
    error messages. Each language is represented by its ISO 639-1 code.

    Attributes:
        FA (str): Represents the Persian language (ISO 639-1 code: 'fa').
        EN (str): Represents the English language (ISO 639-1 code: 'en').
    """

    FA = "FA"  # Persian
    EN = "EN"  # English
