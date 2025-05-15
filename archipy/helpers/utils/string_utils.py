import re
from re import compile

from archipy.helpers.utils.string_utils_constants import StringUtilsConstants


class StringUtils(StringUtilsConstants):
    """String utilities for text normalization, cleaning, and masking.

    This class provides methods for handling Persian and Arabic text, including normalization,
    punctuation cleaning, number conversion, and masking of sensitive information like URLs,
    emails, and phone numbers.
    """

    @classmethod
    def remove_arabic_vowels(cls, text: str) -> str:
        """Removes Arabic vowels (tashkeel) from the text.

        Args:
            text (str): The input text containing Arabic vowels.

        Returns:
            str: The text with Arabic vowels removed.
        """
        return text.translate(cls.arabic_vowel_translate_table)

    @classmethod
    def normalize_persian_chars(cls, text: str) -> str:
        """Normalizes Persian characters to their standard forms.

        Args:
            text (str): The input text containing Persian characters.

        Returns:
            str: The text with Persian characters normalized.
        """
        text = text.translate(cls.alphabet_akoolad_alef_translate_table)
        text = text.translate(cls.alphabet_alef_translate_table)
        text = text.translate(cls.alphabet_be_translate_table)
        text = text.translate(cls.alphabet_pe_translate_table)
        text = text.translate(cls.alphabet_te_translate_table)
        text = text.translate(cls.alphabet_se_translate_table)
        text = text.translate(cls.alphabet_jim_translate_table)
        text = text.translate(cls.alphabet_che_translate_table)
        text = text.translate(cls.alphabet_he_translate_table)
        text = text.translate(cls.alphabet_khe_translate_table)
        text = text.translate(cls.alphabet_dal_translate_table)
        text = text.translate(cls.alphabet_zal_translate_table)
        text = text.translate(cls.alphabet_re_translate_table)
        text = text.translate(cls.alphabet_ze_translate_table)
        text = text.translate(cls.alphabet_zhe_translate_table)
        text = text.translate(cls.alphabet_sin_translate_table)
        text = text.translate(cls.alphabet_shin_translate_table)
        text = text.translate(cls.alphabet_sad_translate_table)
        text = text.translate(cls.alphabet_zad_translate_table)
        text = text.translate(cls.alphabet_ta_translate_table)
        text = text.translate(cls.alphabet_za_translate_table)
        text = text.translate(cls.alphabet_eyn_translate_table)
        text = text.translate(cls.alphabet_gheyn_translate_table)
        text = text.translate(cls.alphabet_fe_translate_table)
        text = text.translate(cls.alphabet_ghaf_translate_table)
        text = text.translate(cls.alphabet_kaf_translate_table)
        text = text.translate(cls.alphabet_gaf_translate_table)
        text = text.translate(cls.alphabet_lam_translate_table)
        text = text.translate(cls.alphabet_mim_translate_table)
        text = text.translate(cls.alphabet_nun_translate_table)
        text = text.translate(cls.alphabet_vav_translate_table)
        text = text.translate(cls.alphabet_ha_translate_table)
        return text.translate(cls.alphabet_ye_translate_table)

    @classmethod
    def normalize_punctuation(cls, text: str) -> str:
        """Normalizes punctuation marks in the text.

        Args:
            text (str): The input text containing punctuation marks.

        Returns:
            str: The text with punctuation marks normalized.
        """
        text = text.translate(cls.punctuation_translate_table1)
        text = text.translate(cls.punctuation_translate_table2)
        text = text.translate(cls.punctuation_translate_table3)
        text = text.translate(cls.punctuation_translate_table4)
        text = text.translate(cls.punctuation_translate_table5)
        text = text.translate(cls.punctuation_translate_table6)
        text = text.translate(cls.punctuation_translate_table7)
        text = text.translate(cls.punctuation_translate_table8)
        text = text.translate(cls.punctuation_translate_table9)
        text = text.translate(cls.punctuation_translate_table10)
        text = text.translate(cls.punctuation_translate_table11)
        text = text.translate(cls.punctuation_translate_table12)
        return text.translate(cls.punctuation_translate_table13)

    @classmethod
    def normalize_numbers(cls, text: str) -> str:
        """Normalizes numbers in the text to English format.

        Args:
            text (str): The input text containing numbers.

        Returns:
            str: The text with numbers normalized to English format.
        """
        text = text.translate(cls.number_zero_translate_table)
        text = text.translate(cls.number_one_translate_table)
        text = text.translate(cls.number_two_translate_table)
        text = text.translate(cls.number_three_translate_table)
        text = text.translate(cls.number_four_translate_table)
        text = text.translate(cls.number_five_translate_table)
        text = text.translate(cls.number_six_translate_table)
        text = text.translate(cls.number_seven_translate_table)
        text = text.translate(cls.number_eight_translate_table)
        return text.translate(cls.number_nine_translate_table)

    @classmethod
    def clean_spacing(cls, text: str) -> str:
        """Cleans up spacing issues in the text, such as non-breaking spaces and zero-width non-joiners.

        Args:
            text (str): The input text with spacing issues.

        Returns:
            str: The text with spacing cleaned up.
        """
        text = text.replace("\u200c", " ")  # ZWNJ
        text = text.replace("\xa0", " ")  # NBSP

        for pattern, repl in cls.character_refinement_patterns:
            text = pattern.sub(repl, text)

        return text

    @classmethod
    def normalize_punctuation_spacing(cls, text: str) -> str:
        """Applies proper spacing around punctuation marks.

        Args:
            text (str): The input text with punctuation spacing issues.

        Returns:
            str: The text with proper spacing around punctuation marks.
        """
        for pattern, repl in cls.punctuation_spacing_patterns:
            text = pattern.sub(repl, text)
        return text

    @classmethod
    def remove_punctuation_marks(cls, text: str) -> str:
        """Removes punctuation marks from the text.

        Args:
            text (str): The input text containing punctuation marks.

        Returns:
            str: The text with punctuation marks removed.
        """
        return text.translate(cls.punctuation_persian_marks_to_space_translate_table)

    @classmethod
    def mask_urls(cls, text: str, mask: str | None = None) -> str:
        """Masks URLs in the text with a specified mask.

        Args:
            text (str): The input text containing URLs.
            mask (str | None): The mask to replace URLs with. Defaults to "MASK_URL".

        Returns:
            str: The text with URLs masked.
        """
        mask = mask or "MASK_URL"
        return compile(r"https?://\S+|www\.\S+").sub(f" {mask} ", text)

    @classmethod
    def mask_emails(cls, text: str, mask: str | None = None) -> str:
        """Masks email addresses in the text with a specified mask.

        Args:
            text (str): The input text containing email addresses.
            mask (str | None): The mask to replace emails with. Defaults to "MASK_EMAIL".

        Returns:
            str: The text with email addresses masked.
        """
        mask = mask or "MASK_EMAIL"
        return compile(r"\S+@\S+\.\S+").sub(f" {mask} ", text)

    @classmethod
    def mask_phones(cls, text: str, mask: str | None = None) -> str:
        """Masks phone numbers in the text with a specified mask.

        Args:
            text (str): The input text containing phone numbers.
            mask (str | None): The mask to replace phone numbers with. Defaults to "MASK_PHONE".

        Returns:
            str: The text with phone numbers masked.
        """
        mask = mask or "MASK_PHONE"
        return compile(r"(?:\+98|0)?(?:\d{3}\s*?\d{3}\s*?\d{4})").sub(f" {mask} ", text)

    @classmethod
    def convert_english_number_to_persian(cls, text: str) -> str:
        """Converts English numbers to Persian numbers in the text.

        Args:
            text (str): The input text containing English numbers.

        Returns:
            str: The text with English numbers converted to Persian numbers.
        """
        table = {
            48: 1776,  # 0
            49: 1777,  # 1
            50: 1778,  # 2
            51: 1779,  # 3
            52: 1780,  # 4
            53: 1781,  # 5
            54: 1782,  # 6
            55: 1783,  # 7
            56: 1784,  # 8
            57: 1785,  # 9
            44: 1548,  # ,
        }
        return text.translate(table)

    @classmethod
    def convert_numbers_to_english(cls, text: str) -> str:
        """Converts Persian/Arabic numbers to English numbers in the text.

        Args:
            text (str): The input text containing Persian/Arabic numbers.

        Returns:
            str: The text with Persian/Arabic numbers converted to English numbers.
        """
        table = {
            1776: 48,  # 0
            1777: 49,  # 1
            1778: 50,  # 2
            1779: 51,  # 3
            1780: 52,  # 4
            1781: 53,  # 5
            1782: 54,  # 6
            1783: 55,  # 7
            1784: 56,  # 8
            1785: 57,  # 9
            1632: 48,  # 0
            1633: 49,  # 1
            1634: 50,  # 2
            1635: 51,  # 3
            1636: 52,  # 4
            1637: 53,  # 5
            1638: 54,  # 6
            1639: 55,  # 7
            1640: 56,  # 8
            1641: 57,  # 9
        }
        return text.translate(table)

    @classmethod
    def convert_add_3digit_delimiter(cls, value: int) -> str:
        """Adds thousand separators to numbers.

        Args:
            value (int): The number to format.

        Returns:
            str: The formatted number with thousand separators.
        """
        return f"{value:,}" if isinstance(value, int) else value

    @classmethod
    def remove_emoji(cls, text: str) -> str:
        """Removes emoji characters from the text.

        Args:
            text (str): The input text containing emojis.

        Returns:
            str: The text with emojis removed.
        """
        emoji_pattern = re.compile(
            r"["
            r"\U0001F600-\U0001F64F"  # emoticons
            r"\U0001F300-\U0001F5FF"  # symbols & pictographs
            r"\U0001F680-\U0001F6FF"  # transport & map symbols
            r"\U0001F1E0-\U0001F1FF"  # flags
            r"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            r"\U0001FA00-\U0001FA6F"  # symbols and pictographs extended-A
            r"\U00002600-\U000026FF"  # miscellaneous symbols (some are emojis)
            r"\U00002700-\U000027BF"  # dingbats (some are emojis)
            r"\U00002190-\U000021FF"  # arrows (some are emojis)
            r"]+",
            re.UNICODE,
        )
        return emoji_pattern.sub(r"", text)

    @classmethod
    def replace_currencies_with_mask(cls, text: str, mask: str | None = None) -> str:
        """Masks currency symbols and amounts in the text.

        Args:
            text (str): The input text containing currency symbols and amounts.
            mask (str | None): The mask to replace currencies with. Defaults to "MASK_CURRENCIES".

        Returns:
            str: The text with currency symbols and amounts masked.
        """
        mask = mask or "MASK_CURRENCIES"
        currency_pattern = compile(r"(\\|zł|£|\$|₡|₦|¥|₩|₪|₫|€|₱|₲|₴|₹|﷼)+")
        return currency_pattern.sub(f" {mask} ", text)

    @classmethod
    def replace_numbers_with_mask(cls, text: str, mask: str | None = None) -> str:
        """Masks numbers in the text.

        Args:
            text (str): The input text containing numbers.
            mask (str | None): The mask to replace numbers with. Defaults to "MASK_NUMBERS".

        Returns:
            str: The text with numbers masked.
        """
        mask = mask or "MASK_NUMBERS"
        numbers = re.findall("[0-9]+", text)
        for number in sorted(numbers, key=len, reverse=True):
            text = text.replace(number, f" {mask} ")
        return text

    @classmethod
    def is_string_none_or_empty(cls, text: str) -> bool:
        """Checks if a string is `None` or empty (after stripping whitespace).

        Args:
            text (str): The input string to check.

        Returns:
            bool: `True` if the string is `None` or empty, `False` otherwise.
        """
        return text is None or isinstance(text, str) and not text.strip()

    @classmethod
    def normalize_persian_text(
        cls,
        text: str,
        *,
        remove_vowels: bool = True,
        normalize_punctuation: bool = True,
        normalize_numbers: bool = True,
        normalize_persian_chars: bool = True,
        mask_urls: bool = False,
        mask_emails: bool = False,
        mask_phones: bool = False,
        mask_currencies: bool = False,
        mask_all_numbers: bool = False,
        remove_emojis: bool = False,
        url_mask: str | None = None,
        email_mask: str | None = None,
        phone_mask: str | None = None,
        currency_mask: str | None = None,
        number_mask: str | None = None,
        clean_spacing: bool = True,
        remove_punctuation: bool = False,
        normalize_punctuation_spacing: bool = False,
    ) -> str:
        """Normalizes Persian text with configurable options.

        Args:
            text (str): The input text to normalize.
            remove_vowels (bool): Whether to remove Arabic vowels. Defaults to `True`.
            normalize_punctuation (bool): Whether to normalize punctuation marks. Defaults to `True`.
            normalize_numbers (bool): Whether to normalize numbers to English format. Defaults to `True`.
            normalize_persian_chars (bool): Whether to normalize Persian characters. Defaults to `True`.
            mask_urls (bool): Whether to mask URLs. Defaults to `False`.
            mask_emails (bool): Whether to mask email addresses. Defaults to `False`.
            mask_phones (bool): Whether to mask phone numbers. Defaults to `False`.
            mask_currencies (bool): Whether to mask currency symbols and amounts. Defaults to `False`.
            mask_all_numbers (bool): Whether to mask all numbers. Defaults to `False`.
            remove_emojis (bool): Whether to remove emojis. Defaults to `False`.
            url_mask (str | None): The mask to replace URLs with. Defaults to `None`.
            email_mask (str | None): The mask to replace email addresses with. Defaults to `None`.
            phone_mask (str | None): The mask to replace phone numbers with. Defaults to `None`.
            currency_mask (str | None): The mask to replace currency symbols and amounts with. Defaults to `None`.
            number_mask (str | None): The mask to replace numbers with. Defaults to `None`.
            clean_spacing (bool): Whether to clean up spacing issues. Defaults to `True`.
            remove_punctuation (bool): Whether to remove punctuation marks. Defaults to `False`.
            normalize_punctuation_spacing (bool): Whether to apply proper spacing around punctuation marks. Defaults to `False`.

        Returns:
            str: The normalized text.
        """
        if not text:
            return text

        # Remove emojis if requested
        if remove_emojis:
            text = cls.remove_emoji(text)

        # Apply normalizations
        if remove_vowels:
            text = cls.remove_arabic_vowels(text)
        if normalize_persian_chars:
            text = cls.normalize_persian_chars(text)
        if normalize_punctuation:
            text = cls.normalize_punctuation(text)
        if remove_punctuation:
            text = cls.remove_punctuation_marks(text)
        if normalize_numbers:
            text = cls.normalize_numbers(text)

        # Apply masking
        if mask_urls:
            text = cls.mask_urls(text, mask=url_mask)
        if mask_emails:
            text = cls.mask_emails(text, mask=email_mask)
        if mask_phones:
            text = cls.mask_phones(text, mask=phone_mask)
        if mask_currencies:
            text = cls.replace_currencies_with_mask(text, mask=currency_mask)
        if mask_all_numbers:
            text = cls.replace_numbers_with_mask(text, mask=number_mask)

        if clean_spacing:
            text = cls.clean_spacing(text)
        if normalize_punctuation_spacing:
            text = cls.normalize_punctuation_spacing(text)

        return text.strip()

    @classmethod
    def snake_to_camel_case(cls, text: str) -> str:
        """Converts snake_case to camelCase.

        Args:
            text (str): The input text in snake_case format.

        Returns:
            str: The text converted to camelCase format.
        """
        if cls.is_string_none_or_empty(text):
            return text

        components = text.split("_")
        # First component remains lowercase, the rest get capitalized
        return components[0] + "".join(x.title() for x in components[1:])

    @classmethod
    def camel_to_snake_case(cls, text: str) -> str:
        """Converts camelCase to snake_case.

        Args:
            text (str): The input text in camelCase format.

        Returns:
            str: The text converted to snake_case format.
        """
        if cls.is_string_none_or_empty(text):
            return text

        # Add underscore before each capital letter and convert to lowercase
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
