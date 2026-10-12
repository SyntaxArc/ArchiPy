Feature: String Utilities

  Scenario: Remove Arabic vowels from text
    Given a text with Arabic vowels "بِسْمِ ٱللَّٰهِ الرَّحْمٰانِ الرَّحِيمِ"
    When the Arabic vowels are removed
    Then the resulting text should be "بسم الله الرحمان الرحیم"

  Scenario: Normalize Persian characters
    Given a text with unnormalized Persian characters "ۀىي"
    When the Persian characters are normalized
    Then the resulting text should be "هیی"

  Scenario: Normalize punctuation marks
    Given a text with mixed punctuation "خوبی?"
    When the punctuation is normalized
    Then the resulting text should be "خوبی؟"

  Scenario Outline: ASCII punctuation is converted only next to Persian text
    Given a text with mixed punctuation "<text>"
    When the punctuation is normalized
    Then the resulting text should be "<expected>"

    Examples:
      | text               | expected           |
      | سلام, دنیا         | سلام، دنیا         |
      | خوبی؟?             | خوبی؟؟             |
      | سلام;              | سلام؛              |
      | ۵۰%                | ۵۰٪                |
      | علی_رضا            | علیـرضا            |
      | 1,000 items        | 1,000 items        |
      | what? yes; 50%     | what? yes; 50%     |
      | user_name@mail.com | user_name@mail.com |
      | https://a.com?x=1  | https://a.com?x=1  |

  Scenario: Normalize numbers to English format
    Given a text with Persian numbers "۱۲۳۴۵۶۷۸۹۰"
    When the numbers are normalized
    Then the resulting text should be "1234567890"

  Scenario: Clean whitespace and spacing issues
    Given a text with spacing issues "Hello  world"
    When the spacing is cleaned
    Then the resulting text should be "Hello world"

  Scenario: Remove punctuation marks
    Given a text with punctuation "Hello, world!!"
    When the punctuation is removed
    Then the resulting text should be "Hello world"

  Scenario: Mask URLs in text
    Given a text containing a URL "Visit https://example.com for info"
    When URLs are masked
    Then the resulting text should be "Visit MASK_URL for info"

  Scenario: Mask emails in text
    Given a text containing an email "Contact me at test@example.com"
    When emails are masked
    Then the resulting text should be "Contact me at MASK_EMAIL"

  Scenario: Mask phone numbers in text
    Given a text containing a phone number "+989123456789"
    When phone numbers are masked
    Then the resulting text should be "MASK_PHONE"

  Scenario: Convert English numbers to Persian
    Given a text with English numbers "1234567890"
    When the English numbers are converted to Persian
    Then the resulting text should be "۱۲۳۴۵۶۷۸۹۰"

  Scenario: Remove emojis from text
    Given a text containing emojis "Hello 😊🌍!"
    When emojis are removed
    Then the resulting text should be "Hello !"

  Scenario: Replace numbers with a mask
    Given a text containing numbers "Order 5 items"
    When numbers are replaced with a mask
    Then the resulting text should be "Order MASK_NUMBERS items"

  Scenario: Replace currencies with a mask
    Given a text containing currency symbols "Price: $100"
    When currencies are replaced with a mask
    Then the resulting text should be "Price: MASK_CURRENCIES 100"

  Scenario: Check if a string is empty
    Given an empty string " "
    When checking if the string is empty
    Then the result should be True

  Scenario: Check if a None string is empty
    Given a None string
    When checking if the string is empty
    Then the result should be True

  Scenario: Apply full text normalization
    Given a complex text "من درب خانه ام را بستم. شماره من ۱۲۳۴ است."
    When full text normalization is applied
    Then the resulting text should be "من درب خانه ام را بستم. شماره من 1234 است."

  Scenario: Noon in its initial presentation form stays a noon
    Given a text with unnormalized Persian characters "ﻧﺎم"
    When the Persian characters are normalized
    Then the resulting text should be "نام"

  Scenario Outline: Unrelated Arabic signs are not turned into letters
    Given a text with unnormalized Persian characters "<text>"
    When the Persian characters are normalized
    Then the resulting text should be "<expected>"

    Examples:
      | text | expected |
      | ؋    | ؋        |
      | ؃    | ؃        |
      | ڧ    | ق        |

  Scenario: Zero-width non-joiners are kept on request
    Given a text with spacing issues "می<ZWNJ>خواهم"
    When the spacing is cleaned keeping zero-width non-joiners
    Then the resulting text should be "می<ZWNJ>خواهم"

  Scenario: Zero-width non-joiners become spaces by default
    Given a text with spacing issues "می<ZWNJ>خواهم"
    When the spacing is cleaned
    Then the resulting text should be "می خواهم"

  Scenario: A backslash is not a currency symbol
    Given a text containing currency symbols "C:\temp"
    When currencies are replaced with a mask
    Then the resulting text should be "C:\temp"

  Scenario: A numeric mask is applied in a single pass
    Given a text containing numbers "Order 5 and 12 items"
    When numbers are replaced with the mask "NUM1"
    Then the resulting text should be "Order NUM1 and NUM1 items"

  Scenario Outline: Punctuation spacing leaves file names and domains alone
    Given a text "<text>"
    When punctuation spacing is applied
    Then the resulting text should be "<expected>"

    Examples:
      | text        | expected    |
      | file.txt    | file.txt    |
      | example.com | example.com |
      | سلام.خوبی   | سلام. خوبی  |

  Scenario Outline: Snake case converts to camel case without touching inner capitals
    Given a text "<text>"
    When it is converted to camel case
    Then the resulting text should be "<expected>"

    Examples:
      | text          | expected    |
      | user_ID       | userID      |
      | my_url_parser | myUrlParser |
      | simple        | simple      |

  Scenario Outline: Thousand separators accept non-integer input
    Given a text "<text>"
    When the value is formatted with thousand separators
    Then the resulting text should be "<expected>"

    Examples:
      | text    | expected  |
      | 1234567 | 1,234,567 |
      | abc     | abc       |
