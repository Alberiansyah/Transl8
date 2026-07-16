from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class EntityMap:
    entries: dict[str, str] = field(default_factory=dict)
    _counter: int = 0

    def add(self, entity_text: str, placeholder: str) -> str:
        self.entries[placeholder] = entity_text
        return placeholder

    def restore(self, text: str) -> str:
        for placeholder, original in self.entries.items():
            text = text.replace(placeholder, original)
        return text


class NERExtractor:
    def __init__(self):
        self.nlp = None

    def _load(self):
        if self.nlp is not None:
            return
        from app.config import SPACY_MODEL
        try:
            import spacy
            self.nlp = spacy.load(SPACY_MODEL)
        except OSError:
            import spacy
            spacy.cli.download(SPACY_MODEL)
            self.nlp = spacy.load(SPACY_MODEL)

    def detect_entities(self, texts: list[str]) -> dict[str, str]:
        """Detect entities across all texts, return mapping original -> unique key."""
        self._load()
        entity_map = {}

        for text in texts:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.text not in entity_map:
                    key = f"__ENT{len(entity_map)}__"
                    entity_map[ent.text] = key

        return entity_map

    def replace_entities(self, text: str, entity_map: dict[str, str]) -> str:
        """Replace known entities with placeholder keys."""
        for original, key in entity_map.items():
            text = text.replace(original, key)
        return text

    def restore_entities(self, text: str, entity_map: dict[str, str]) -> str:
        """Restore placeholder keys back to original entity text."""
        for original, key in entity_map.items():
            text = text.replace(key, original)
        return text
