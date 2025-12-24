"""language detection helpers"""
import re

_LANGUAGE_HINTS = {
    "he": re.compile(r"[\u0590-\u05FF]"),
    "ar": re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
}


def detect_language(text: str) -> str:
    """detect language based on script. defaults to english."""
    if not text:
        return "en"

    counts = {}
    for code, pattern in _LANGUAGE_HINTS.items():
        counts[code] = len(pattern.findall(text))

    best_lang = max(counts, key=counts.get)
    if counts.get(best_lang, 0) > 0:
        return best_lang
    return "en"
