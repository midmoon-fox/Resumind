"""Recover literal source spans from typographic/case-only model quote changes."""

from app.modules.ai.errors import AiFailure

_TYPOGRAPHY = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def _indexed(text):
    normalized, positions = [], []
    for index, character in enumerate(text):
        for char in character.translate(_TYPOGRAPHY).casefold():
            if char.isspace():
                char = " "
                if normalized and normalized[-1] == " ":
                    continue
            normalized.append(char)
            positions.append(index)
    return "".join(normalized), positions


def literal_quote(quote, visible_source):
    if quote and quote in visible_source:
        return quote
    needle, _ = _indexed(quote)
    needle = needle.strip()
    source, positions = _indexed(visible_source)
    position = source.find(needle) if needle else -1
    if position < 0 or source.find(needle, position + 1) >= 0:
        raise AiFailure("MODEL_SOURCE_INVALID", "岗位引文无法唯一对应本次输入原文")
    # Return the original text, never the model's rewritten quotation.
    return visible_source[positions[position] : positions[position + len(needle) - 1] + 1]
