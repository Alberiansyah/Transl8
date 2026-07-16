from __future__ import annotations

import re
from app.config import MAX_LINE_LENGTH
from app.translator.ner import EntityMap
from app.translator.glossary import Glossary


def fix_line_length(text: str, max_len: int = MAX_LINE_LENGTH) -> str:
    lines = text.split("\n")
    fixed = []

    for line in lines:
        if len(line) <= max_len:
            fixed.append(line)
            continue

        words = line.split()
        current = ""
        result_lines = []

        for word in words:
            if current and len(current) + 1 + len(word) > max_len:
                result_lines.append(current)
                current = word
            else:
                current = f"{current} {word}".strip() if current else word

        if current:
            result_lines.append(current)

        fixed.append("\n".join(result_lines[:2]))

    return "\n".join(fixed)


def fix_punctuation(text: str) -> str:
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'\.{3,}', '...', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def restore_formatting_tags(original: str, translated: str) -> str:
    tag_pattern = re.compile(r'\{\\[^}]*\}')
    tags = tag_pattern.findall(original)

    if not tags:
        return translated

    prefix_tags = []
    for tag in tags:
        if original.startswith(tag) or (original[:original.index(tag[0])].strip() == "" if tag[0] in original else False):
            prefix_tags.append(tag)
        else:
            break

    if prefix_tags:
        tag_str = "".join(prefix_tags)
        translated = tag_str + translated

    return translated


def postprocess_translated(
    translated_text: str,
    original_text: str,
    entity_map: EntityMap | None = None,
    glossary: Glossary | None = None,
) -> str:
    text = translated_text

    if entity_map:
        text = entity_map.restore(text)

    if glossary:
        text = glossary.restore(text)

    text = fix_punctuation(text)
    text = fix_line_length(text)
    text = restore_formatting_tags(original_text, text)

    return text
