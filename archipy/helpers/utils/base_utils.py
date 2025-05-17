import re

from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.helpers.utils.error_utils import ErrorUtils
from archipy.helpers.utils.file_utils import FileUtils
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.helpers.utils.password_utils import PasswordUtils
from archipy.helpers.utils.string_utils import StringUtils
from archipy.helpers.utils.totp_utils import TOTPUtils
from archipy.models.errors import (
    InvalidLandlineNumberError,
    InvalidNationalCodeError,
    InvalidPhoneNumberError,
)


class BaseUtils(ErrorUtils, DatetimeUtils, PasswordUtils, JWTUtils, TOTPUtils, FileUtils, StringUtils):
    """A utility class that combines multiple utility functionalities into a single class.

    This class inherits from various utility classes to provide a centralized place for common utility methods.
    """

    @staticmethod
    def sanitize_iranian_landline_or_phone_number(landline_or_phone_number: str) -> str:
        """Sanitizes an Iranian landline or mobile phone number by removing non-numeric characters and standardizing the format.

        Args:
            landline_or_phone_number (str): The phone number to sanitize.

        Returns:
            str: The sanitized phone number in a standardized format.
        """
        # Remove non-numeric characters
        cleaned_number = re.sub(r"\D", "", landline_or_phone_number)

        # Standardize international format to local Iran format
        if cleaned_number.startswith("0098"):  # Handles "0098"
            cleaned_number = "0" + cleaned_number[4:]  # Replace "0098" with "0"
        elif cleaned_number.startswith("98"):  # Handles "+98"
            cleaned_number = "0" + cleaned_number[2:]  # Replace "98" with "0"

        # Ensure mobile numbers start with '09'
        if len(cleaned_number) == 10 and cleaned_number.startswith("9"):
            cleaned_number = "0" + cleaned_number  # Convert "9123456789" → "09123456789"

        return cleaned_number

    @classmethod
    def validate_iranian_phone_number(cls, phone_number: str) -> None:
        """Validates an Iranian mobile phone number.

        Args:
            phone_number (str): The phone number to validate.

        Raises:
            InvalidPhoneNumberError: If the phone number is invalid.
        """
        # Sanitize the input to remove spaces, dashes, or other non-numeric characters
        sanitized_number = cls.sanitize_iranian_landline_or_phone_number(phone_number)
        # Define the regular expression pattern for Iranian phone numbers
        iranian_mobile_pattern = re.compile(r"^09\d{9}$")  # Mobile numbers

        # Check if the phone number matches either mobile or landline pattern
        if not iranian_mobile_pattern.match(sanitized_number):
            raise InvalidPhoneNumberError(phone_number)

    @classmethod
    def validate_iranian_landline_number(cls, landline_number: str) -> None:
        """Validates an Iranian landline number.

        Args:
            landline_number (str): The landline number to validate.

        Raises:
            InvalidLandlineNumberError: If the landline number is invalid.
        """
        # Sanitize the input to remove spaces, dashes, or other non-numeric characters
        sanitized_number = cls.sanitize_iranian_landline_or_phone_number(landline_number)
        # Landline examples: `0` + 2 to 4-digit area code + 7 to 8-digit local number
        iranian_landline_pattern = re.compile(r"^0\d{2,4}\d{7,8}$")

        if not iranian_landline_pattern.match(sanitized_number):
            raise InvalidLandlineNumberError(landline_number)

    @classmethod
    def validate_iranian_national_code_pattern(cls, national_code: str) -> None:
        """Validates an Iranian National ID number using the official algorithm.
        To see how the algorithm works, see http://www.aliarash.com/article/codemeli/codemeli.htm

        The algorithm works by:
        1. Checking if the ID is exactly 10 digits
        2. Multiplying each digit (except the last) by its position weight
        3. Summing these products
        4. Calculating the remainder when divided by 11
        5. Comparing the check digit based on specific rules

        Args:
            national_code (str): A string containing the national ID to validate.

        Raises:
            InvalidNationalCodeError: If the ID is invalid due to length or checksum.
        """

        def _validate_length(national_code: str) -> None:
            """Validates that the national code is exactly 10 digits long.

            Args:
                national_code (str): The national code to validate.

            Raises:
                InvalidNationalCodeError: If the length is not 10 digits.
            """
            if not len(national_code) == 10:
                raise InvalidNationalCodeError(national_code)

        def _calculate_weighted_sum(national_code: str) -> int:
            """Calculates the weighted sum of the national code digits.

            Args:
                national_code (str): The national code to calculate the weighted sum for.

            Returns:
                int: The weighted sum of the national code digits.
            """
            return sum(int(digit) * (10 - i) for i, digit in enumerate(national_code[:-1]))

        def _get_checksums(national_code: str) -> tuple[int, int]:
            """Calculates the expected and actual checksums for the national code.

            Args:
                national_code (str): The national code to calculate checksums for.

            Returns:
                tuple[int, int]: A tuple containing the calculated checksum and the actual checksum.
            """
            weighted_sum = _calculate_weighted_sum(national_code)
            remainder = weighted_sum % 11

            calculated_checksum = remainder if remainder < 2 else 11 - remainder
            actual_checksum = int(national_code[-1])

            return calculated_checksum, actual_checksum

        _validate_length(national_code)
        calculated_checksum, actual_checksum = _get_checksums(national_code)
        if calculated_checksum != actual_checksum:
            raise InvalidNationalCodeError(national_code)
