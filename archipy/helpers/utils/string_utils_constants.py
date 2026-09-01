"""Constants for string utility helpers."""

import re
from re import compile as re_compile


def compile_patterns(patterns: list[tuple[str, str]]) -> list[tuple[re.Pattern[str], str]]:
    """Compile regex patterns with their replacement strings.

    Args:
        patterns: List of tuples containing (pattern, replacement) pairs.

    Returns:
        List of tuples containing (compiled_pattern, replacement) pairs.
    """
    return [(re_compile(pattern), repl) for pattern, repl in patterns]


class StringUtilsConstants:
    """Constants for string utility operations including translation tables and regex patterns."""

    arabic_vowel_translate_table = str.maketrans(
        dict.fromkeys(
            "\u064e\u064f\u0650\u0652\u0651\u0653\u064b\u064c\u0621\u064d\u0670"  # Normal vowels (Fatha, Damma, etc)
            "\u06d6\u06d7\u06d8\u06d9\u06da\u06db",  # Quranic marks
            "",
        ),
    )

    # replace 'آ|ﺁ' with 'آ'
    alphabet_akoolad_alef_translate_table = str.maketrans(dict.fromkeys("\ufe81", "\u0622"))

    # replace 'ٳ|ٲ|ٱ|إ|ﺍ|أ|ٵ | ﺎ' with 'ا'
    alphabet_alef_translate_table = str.maketrans(
        dict.fromkeys("\ufe8e\u0672\u0671\u0625\ufe8d\u0623\u0675\u0673", "\u0627"),
    )

    # replace 'ٮ|ݕ|ٻ|ﺐ|ﺏ|ﺑ' with "ب"
    alphabet_be_translate_table = str.maketrans(dict.fromkeys("\ufe90\ufe8f\ufe91\u067b\u066e", "\u0628"))

    # replace 'ݕ|ݒ|ݐ|ڀ|ﭖ|ﭗ|ﭙ|ﺒ|ﭘ' with "پ"
    alphabet_pe_translate_table = str.maketrans(
        dict.fromkeys("\ufb56\ufb57\ufb59\ufe92\ufb58\u0680\u0750\u0752\u0755", "\u067e"),
    )

    # replace 'ﭡ|ٺ|ٹ|ﭞ|ٿ|ټ|ﺕ|ﺗ|ﺖ|ﺘ|ݓ' with "ت"
    alphabet_te_translate_table = str.maketrans(
        dict.fromkeys("\ufb61\u067a\u0679\ufb5e\u067f\u067c\ufe95\ufe97\ufe96\ufe98\u0753", "\u062a"),
    )
    # replace ﺙ|ﺛ|ٽ|ﺚ|ﺜ with "ث"
    alphabet_se_translate_table = str.maketrans(dict.fromkeys("\ufe99\ufe9b\u067d\ufe9a\ufe9c", "\u062b"))

    # replace "ﺞ|ﺝ|ﺠ|ﺟ| " with "ج"
    alphabet_jim_translate_table = str.maketrans(dict.fromkeys("\ufe9d\ufea0\ufe9f\ufe9e\u06da", "\u062c"))

    # replace "ﭻ|ڿ|ݘ|ڄ|ڇ|ڃ|ﭽ|ﭼ" with "چ"
    alphabet_che_translate_table = str.maketrans(
        dict.fromkeys("\u0683\ufb7d\ufb7c\u0687\u0684\u0758\u06bf\ufb7b", "\u0686"),
    )

    # replace "ﺡ|ﺢ|ﺤ|څ|ځ|ﺣ" with "ح"
    alphabet_he_translate_table = str.maketrans(dict.fromkeys("\ufea2\ufea4\u0685\u0681\ufea3\ufea1", "\u062d"))

    # replace "ݗ|څ|ڂ|ﺥ|ﺦ|ﺨ|ﺧ" with "خ"
    alphabet_khe_translate_table = str.maketrans(dict.fromkeys("\ufea5\ufea6\ufea8\ufea7\u0682\u0757", "\u062e"))

    # replace "ܥ|ڍ|ڈ|ڊ|ﺪ|ﺩ|ډ" with "د"
    alphabet_dal_translate_table = str.maketrans(dict.fromkeys("\u0689\ufeaa\ufea9\u068a\u0688\u068d\u0725", "\u062f"))

    # replace "ڌ|ڎ|ڏ|ڐ|ﺫ|ﺬ|ﻧ" with "ذ"
    alphabet_zal_translate_table = str.maketrans(dict.fromkeys("\ufeab\ufeac\ufee7\u0690\u068f\u068e\u068c", "\u0630"))

    # replace "ۯ|ڑ|ڒ|ړ|ڔ|ڕ|ږ|ڒ|ڑ|ڕ|ﺭ|ﺮ|ڗ" with "ر"
    alphabet_re_translate_table = str.maketrans(
        dict.fromkeys("\u0697\u0692\u0691\u0695\ufead\ufeae\u0696\u0694\u0693\u0692\u0691\u06ef", "\u0631"),
    )

    # replace "ﺰ|ﺯ" with "ز"
    alphabet_ze_translate_table = str.maketrans(dict.fromkeys("\ufeb0\ufeaf", "\u0632"))

    # replace "ﮋ|ڙ|ﮊ" with "ژ"
    alphabet_zhe_translate_table = str.maketrans(dict.fromkeys("\ufb8a\u0699\ufb8b", "\u0698"))

    # replace  r"ۣښ|ݭ|ݜ|ﺱ|ﺲ|ښ|ﺴ|ﺳ|ڛ|ۣ	"ݽ|ݾ|with r "س"
    alphabet_sin_translate_table = str.maketrans(
        dict.fromkeys("\u076d\u075c\ufeb1\ufeb2\ufeb4\ufeb3\u069b\u069a\u06e3\u077e\u077d", "\u0633"),
    )

    # replace "ۺ|ڜ|ﺵ|ﺶ|ﺸ|ﺷ" with "ش"
    alphabet_shin_translate_table = str.maketrans(dict.fromkeys("\ufeb5\ufeb6\ufeb8\ufeb7\u069c\u06fa", "\u0634"))

    # replace "ڝ|ﺺ|ﺼ|ﺻ |ﺹ" with "ص"
    alphabet_sad_translate_table = str.maketrans(dict.fromkeys("\ufeb9\ufeba\ufebc\ufebb\u069d", "\u0635"))

    # replace "ڞ|ۻ|ﺽ|ﺾ|ﺿ|ﻀ"  with "ض"
    alphabet_zad_translate_table = str.maketrans(dict.fromkeys("\ufebd\ufebe\ufebf\ufec0\u06fb\u069e", "\u0636"))

    # replace "ﻁ|ﻂ|ﻃ|ﻄ" with "ط"
    alphabet_ta_translate_table = str.maketrans(dict.fromkeys("\ufec1\ufec2\ufec3\ufec4", "\u0637"))

    # replace "ڟ|ﻆ|ﻇ|ﻈ|ﻅ" with "ظ"
    alphabet_za_translate_table = str.maketrans(dict.fromkeys("\ufec6\ufec7\ufec8\u069f\ufec5", "\u0638"))

    # replace "ڠ|ﻉ|ﻊ|ﻋ|ﻌ" with "ع"
    alphabet_eyn_translate_table = str.maketrans(dict.fromkeys("\u06a0\ufec9\ufeca\ufecb\ufecc", "\u0639"))

    # replace "ݞ|ݝ|ﻎ|ۼ|ﻍ|ﻐ|ﻏ|ݟ" with "غ"
    alphabet_gheyn_translate_table = str.maketrans(
        dict.fromkeys("\ufece\u06fc\ufecd\ufed0\ufecf\u075d\u075e\u075f", "\u063a"),
    )

    # replace "ڢ|ڣ|ڢ|ڣ|ڤ|ڦ|ڥ|ڡ|ﻒ|ﻑ|ﻔ|ﻓ" with "ف"
    alphabet_fe_translate_table = str.maketrans(
        dict.fromkeys("\ufed2\ufed1\ufed4\ufed3\u06a1\u06a5\u06a6\u06a4\u0603\u06a3\u06a2", "\u0641"),
    )

    # replace "؋|ڧ|ڨ|ﻕ|ﻖ|ﻗ|ﻘ" with "ق"
    alphabet_ghaf_translate_table = str.maketrans(dict.fromkeys("\ufed5\ufed6\ufed7\u06a7\u06a8\u060b\ufed8", "\u0642"))

    # replace "ݿ|ڮ|ڬ|ݤ|ݣ|ݢ|ڭ|ﻚ|ﮎ|ﻜ|ﮏ|ګ|ﻛ|ﮑ|ﮐ|ڪ|ك|ﻙ" with "ک"
    alphabet_kaf_translate_table = str.maketrans(
        dict.fromkeys(
            "\u06ad\ufeda\ufb8e\ufedc\ufb8f\u06ab\ufedb"
            "\ufb91\ufb90\u06aa\u0643\u0762\u0763\u0764"
            "\u06ac\u06ae\u077f\ufed9",
            "\u06a9",
        ),
    )
    # replace  "ڴ|ڳ|ڲ|ڰ|ڱ|ﮚ|ﮒ|ﮓ|ﮕ|ﮔ" with "گ"
    alphabet_gaf_translate_table = str.maketrans(
        dict.fromkeys("\ufb9a\ufb92\ufb93\ufb95\ufb94\u06b1\u06b0\u06b2\u06b3\u06b4", "\u06af"),
    )

    # replace "ڵ|ڶ|ڸ|ڷ|ݪ|ﻝ|ﻞ|ﻠ|ڵ | ﻟ" with "ل"
    alphabet_lam_translate_table = str.maketrans(
        dict.fromkeys("\ufedf\ufedd\ufede\ufee0\u076a\u06b7\u06b8\u06b6\u06b5", "\u0644"),
    )

    # replace "ݥ|ݦ|ﻡ|ﻤ|ﻢ|ﻣ" with "م"
    alphabet_mim_translate_table = str.maketrans(dict.fromkeys("\ufee1\ufee4\ufee2\ufee3\u0766\u0765", "\u0645"))

    # replace "ڹ|ں|ڽ|ڻ|ݧ|ݨ|ݩ|ڼ|ﻦ|ﻥ|ﻨ" with "ن"
    alphabet_nun_translate_table = str.maketrans(
        dict.fromkeys("\u06bc\ufee6\ufee5\ufee8\u0769\u0768\u0767\u06bb\u06bd\u06ba\u06b9", "\u0646"),
    )

    # replace "ۄ|ۆ|ۊ|ވ|ﯙ|ۈ|ۋ|ﺆ|ۊ|ۇ|ۏ|ۅ|ۉ|ﻭ|ﻮ|ؤ" with "و"
    alphabet_vav_translate_table = str.maketrans(
        dict.fromkeys(
            "\u0788\ufbd9\u06c8\u06cb\ufe86\u06ca\u06c7\u06cf\u06c5\u06c9\ufeed\ufeee\u0624\u06c6\u06c4",
            "\u0648",
        ),
    )
    # replace "ܝ|ܤ|ܣ|ﺔ|ﻬ|ھ|ﻩ|ﻫ|ﻪ|ۀ|ە|ة|ہ|ﮭ|ﺓ" with "ه"
    alphabet_ha_translate_table = str.maketrans(
        dict.fromkeys(
            "\ufe93\ufbad\ufe94\ufeec\u06be\ufee9\ufeeb\ufeea\u06c0\u06d5\u0629\u06c1\u0723\u0724\u071d",
            "\u0647",
        ),
    )

    # replace "ﺋ|ؿ|ؾ|ؽ|ۑ|ٸ|ﭛ|ﻯ|ۍ|ﻰ|ﻱ|ﻲ|ﻳ|ﻴ|ﯼ|ې|ﯽ|ﯾ|ﯿ|ێ|ے|ى|ي|ﺉ|ﺌ |ﯨ" with "ی"
    alphabet_ye_translate_table = str.maketrans(
        dict.fromkeys(
            "\ufbe8\ufb5b\ufeef\u06cd\ufef0\ufef1\ufef2\ufef3\ufef4\ufbfc"
            "\u06d0\ufbfd\ufbfe\ufbff\u06ce\u06d2\u0649\u064a\u0678"
            "\u06d1\u063d\u063e\u063f\ufe89\ufe8b\ufe8c",
            "\u06cc",
        ),
    )
    # replace '¬' with ' '
    punctuation_translate_table1 = str.maketrans(dict.fromkeys("\u00ac", "\u0020"))

    # replace '•|·|●|·|・|∙|｡|ⴰ' with '.'
    punctuation_translate_table2 = str.maketrans(
        dict.fromkeys("\u2022\u00b7\u25cf\u0387\u30fb\u2219\uff61\u2d30", "\u002e"),
    )

    # replace ',|٬|٫|‚|，' with '،'
    punctuation_translate_table3 = str.maketrans(dict.fromkeys("\u002c\u066c\u066b\u201a\uff0c", "\u060c"))

    # replace 'ʕ | ? | ⁉ | � ' with '؟'
    punctuation_translate_table4 = str.maketrans(dict.fromkeys("\u0295\u003f\u2049\ufffd", "\u061f"))

    # replace '‼ | ❕ ' with '!'
    punctuation_translate_table5 = str.maketrans(dict.fromkeys("\u203c\u2755", "\u0021"))

    # replace '_ ' with 'ـ'
    punctuation_translate_table6 = str.maketrans(dict.fromkeys("\u005f", "\u0640"))

    # replace ' － | ━ | − | ‐ | ‑ | – | — | ─ | − | ー | ⁃ (hyphen bullet : not supported by pycharm) |  ' with '-'
    punctuation_translate_table7 = str.maketrans(
        dict.fromkeys("\uff0d\u2501\u2212\u2010\u2011\u2013\u2014\u2500\u2212\u30fc\u2043", "\u002d"),
    )

    # replace '‹ |《 | ﴾ ' with '«'
    punctuation_translate_table8 = str.maketrans(dict.fromkeys("\u2039\u300a\ufd3e", "\u00ab"))

    # replace '› | 》| ﴿ ' with '»'
    punctuation_translate_table9 = str.maketrans(dict.fromkeys("\u203a\u300b\ufd3f", "\u00bb"))

    # replace ';' with '؛'
    punctuation_translate_table10 = str.maketrans(dict.fromkeys("\u003b", "\u061b"))

    # replace '%' with '٪'
    punctuation_translate_table11 = str.maketrans(dict.fromkeys("\u0025", "\u066a"))

    # replace "  ˈ | ‘ | ’ | “ | ”  " with " ' "
    punctuation_translate_table12 = str.maketrans(dict.fromkeys("\u02c8\u2018\u2019\u201c\u201d", "\u0027"))

    # replace '：' with ': '
    punctuation_translate_table13 = str.maketrans(dict.fromkeys("\uff1a", "\u003a"))

    character_refinement_patterns: list = compile_patterns(
        [
            (r" +", " "),  # remove extra spaces
            (r"\n\n+", "\n"),  # remove extra newlines
            (r" ?\.\.\.", " …"),  # replace 3 dots
        ],
    )

    punctuation_after = r"\.:!،؛؟»\]\)\}"
    punctuation_before = r"«\[\(\{"

    punctuation_spacing_patterns = compile_patterns(
        [
            (f" ([{punctuation_after}])", r"\1"),
            (f"([{punctuation_before}]) ", r"\1"),
            (
                f"([{punctuation_after[:3]}])([^ {punctuation_after}" + r"\d])",
                r"\1 \2",
            ),
            (
                f"([{punctuation_after[3:]}])([^ {punctuation_after}])",
                r"\1 \2",
            ),
            (f"([^ {punctuation_before}])([{punctuation_before}])", r"\1 \2"),
        ],
    )

    # replace '۰|٠' with '0'
    number_zero_translate_table = str.maketrans(dict.fromkeys("\u06f0\u0660", "\u0030"))

    # replace '۱|١' with '1'
    number_one_translate_table = str.maketrans(dict.fromkeys("\u06f1\u0661", "\u0031"))

    # replace '۲|٢' with '2'
    number_two_translate_table = str.maketrans(dict.fromkeys("\u06f2\u0662", "\u0032"))

    # replace '۳|٣' with '3'
    number_three_translate_table = str.maketrans(dict.fromkeys("\u06f3\u0663", "\u0033"))

    # replace '۴|٤' with '4'
    number_four_translate_table = str.maketrans(dict.fromkeys("\u06f4\u0664", "\u0034"))

    # replace '۵|٥' with '5'
    number_five_translate_table = str.maketrans(dict.fromkeys("\u06f5\u0665", "\u0035"))

    # replace '۶|٦' with '6'
    number_six_translate_table = str.maketrans(dict.fromkeys("\u06f6\u0666", "\u0036"))

    # replace '۷|٧' with '7'
    number_seven_translate_table = str.maketrans(dict.fromkeys("\u06f7\u0667", "\u0037"))

    # replace '۸|٨' with '8'
    number_eight_translate_table = str.maketrans(dict.fromkeys("\u06f8\u0668", "\u0038"))

    # replace '۹|٩' with '9'
    number_nine_translate_table = str.maketrans(dict.fromkeys("\u06f9\u0669", "\u0039"))

    # replace ' «|» | . | : | ، | ؛ | ؟ | [|] | (|) | {|} | - | ـ | ٪ | ! | ' | " | # | + | / |' with ' '
    punctuation_persian_marks_to_space_translate_table = str.maketrans(
        dict.fromkeys(
            "\u002e\u003a\u0021\u060c\u061b\u061f\u00bb\u005d"
            "\u0029\u007d\u00ab\u005b\u0028\u007b\u002d\u0640\u066a\u0021\u0027\u0022\u0023"
            "\u002b\u002f",
            "\u0020",
        ),
    )
