"""Check repeated printable fragments without disclosing private text in errors."""
from collections import defaultdict
import re
import unicodedata


def missing_text_paths(text, expected):
    normalize = lambda value: re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))
    actual = normalize(text)
    grouped = defaultdict(list)
    for path, value in expected:
        fragment = normalize(value)
        if fragment:
            grouped[fragment].append(path)
    missing = []
    for fragment, paths in grouped.items():
        # Checking only membership lets one retained duplicate hide several omitted copies.
        available = actual.count(fragment)
        missing.extend(paths[available:])
    return missing
