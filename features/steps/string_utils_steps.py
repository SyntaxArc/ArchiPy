from behave import given, then, when

from archipy.helpers.utils.string_utils import StringUtils
from features.test_helpers import get_current_scenario_context


@given('a text with Arabic vowels "{text}"')
def step_given_text_with_arabic_vowels(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the Arabic vowels are removed")
def step_when_arabic_vowels_removed(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text)
    scenario_context.store("result_text", result_text)


@then('the resulting text should be "{expected_text}"')
def step_then_resulting_text_should_be(context, expected_text):
    scenario_context = get_current_scenario_context(context)
    result_text = scenario_context.get("result_text")
    assert result_text == expected_text.replace("<ZWNJ>", "\u200c")


@given('a text with unnormalized Persian characters "{text}"')
def step_given_persian_chars(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the Persian characters are normalized")
def step_when_persian_chars_normalized(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_chars(test_text)
    scenario_context.store("result_text", result_text)


@given('a text with mixed punctuation "{text}"')
def step_given_text_with_punctuation(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the punctuation is normalized")
def step_when_punctuation_normalized(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_punctuation(test_text)
    scenario_context.store("result_text", result_text)


@given('a text with Persian numbers "{text}"')
def step_given_text_with_persian_numbers(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the numbers are normalized")
def step_when_numbers_normalized(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_numbers(test_text)
    scenario_context.store("result_text", result_text)


@given('a text containing numbers "{text}"')
def step_given_text_with_numbers(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("numbers are replaced with a mask")
def step_when_numbers_replaced_with_mask(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, mask_all_numbers=True)
    scenario_context.store("result_text", result_text)


@given('a text containing currency symbols "{text}"')
def step_given_text_with_currency(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("currencies are replaced with a mask")
def step_when_currencies_replaced_with_mask(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, mask_currencies=True)
    scenario_context.store("result_text", result_text)


@given('an empty string "{text}"')
def step_given_empty_string(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@given("a None string")
def step_given_none_string(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", None)


@when("checking if the string is empty")
def step_when_checking_empty_string(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result = StringUtils.is_string_none_or_empty(test_text)
    scenario_context.store("result", result)


@given('a complex text "{text}"')
def step_given_complex_text(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("full text normalization is applied")
def step_when_text_is_normalized(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(
        test_text,
        remove_vowels=True,
        normalize_punctuation=True,
        normalize_numbers=True,
        normalize_persian_chars=True,
        clean_spacing=True,
        remove_emojis=True,
    )
    scenario_context.store("result_text", result_text)


@given('a text with spacing issues "{text}"')
def step_given_text_with_spacing_issues(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text.replace("<ZWNJ>", "\u200c"))


@when("the spacing is cleaned")
def step_when_spacing_cleaned(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.clean_spacing(test_text)
    scenario_context.store("result_text", result_text)


@given('a text with punctuation "{text}"')
def step_given_text_with_punctuation_marks(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the punctuation is removed")
def step_when_punctuation_removed(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, remove_punctuation=True)
    scenario_context.store("result_text", result_text)


@given('a text containing a URL "{text}"')
def step_given_text_with_url(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("URLs are masked")
def step_when_urls_masked(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, mask_urls=True)
    scenario_context.store("result_text", result_text)


@given('a text containing an email "{text}"')
def step_given_text_with_email(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("emails are masked")
def step_when_emails_masked(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, mask_emails=True)
    scenario_context.store("result_text", result_text)


@given('a text containing a phone number "{text}"')
def step_given_text_with_phone(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("phone numbers are masked")
def step_when_phone_numbers_masked(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.normalize_persian_text(test_text, mask_phones=True)
    scenario_context.store("result_text", result_text)


@given('a text with English numbers "{text}"')
def step_given_text_with_english_numbers(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("the English numbers are converted to Persian")
def step_when_english_numbers_converted(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.convert_english_number_to_persian(test_text)
    scenario_context.store("result_text", result_text)


@given('a text containing emojis "{text}"')
def step_given_text_with_emojis(context, text):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("test_text", text)


@when("emojis are removed")
def step_when_emojis_removed(context):
    scenario_context = get_current_scenario_context(context)
    test_text = scenario_context.get("test_text")
    result_text = StringUtils.remove_emoji(test_text)
    scenario_context.store("result_text", result_text)


@when("the spacing is cleaned keeping zero-width non-joiners")
def step_when_spacing_cleaned_keep_zwnj(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("result_text", StringUtils.clean_spacing(scenario_context.get("test_text"), keep_zwnj=True))


@when('numbers are replaced with the mask "{mask}"')
def step_when_numbers_replaced_with_custom_mask(context, mask):
    scenario_context = get_current_scenario_context(context)
    result = StringUtils.normalize_persian_text(scenario_context.get("test_text"), mask_all_numbers=True, number_mask=mask)
    scenario_context.store("result_text", result)


@given('a text "{text}"')
def step_given_plain_text(context, text):
    get_current_scenario_context(context).store("test_text", text)


@when("punctuation spacing is applied")
def step_when_punctuation_spacing(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("result_text", StringUtils.normalize_punctuation_spacing(scenario_context.get("test_text")))


@when("it is converted to camel case")
def step_when_camel_case(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("result_text", StringUtils.snake_to_camel_case(scenario_context.get("test_text")))


@when("the value is formatted with thousand separators")
def step_when_thousand_separators(context):
    scenario_context = get_current_scenario_context(context)
    text = scenario_context.get("test_text")
    value = int(text) if text.isdigit() else text
    scenario_context.store("result_text", StringUtils.convert_add_3digit_delimiter(value))
