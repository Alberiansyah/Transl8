from __future__ import annotations

import time
import logging
import threading
from typing import Callable
from dataclasses import dataclass, field

from app.translator.parser import SubtitleFile
from app.translator.context_batcher import ContextBatcher
from app.translator.glossary import Glossary
from app.translator.nllb_engine import NLLBEngine

logger = logging.getLogger(__name__)


@dataclass
class TranslationProgress:
    total_batches: int = 0
    completed_batches: int = 0
    status: str = "idle"
    error: str | None = None
    last_batch_seconds: float = 0.0
    device_used: str = "cpu"
    completed_lines: int = 0
    total_files: int = 1
    completed_files: int = 0
    current_file: str = ""

    @property
    def percent(self) -> float:
        if self.total_batches == 0:
            return 0
        return (self.completed_batches / self.total_batches) * 100


class TranslationPipeline:
    def __init__(self):
        self.nllb = NLLBEngine()
        self.batcher = ContextBatcher()
        self.progress = TranslationProgress()

    def translate(
        self,
        sub_file: SubtitleFile,
        source_lang: str,
        target_lang: str,
        glossary: Glossary | None = None,
        batch_size: int = 15,
        num_beams: int = 2,
        engine_batch_size: int = 16,
        device: str = "auto",
        on_progress: Callable[[TranslationProgress], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[str]:
        self.progress = TranslationProgress()
        self.batcher.batch_size = batch_size

        lines = sub_file.lines
        if not lines:
            return []

        original_texts = [l.text for l in lines]

        self.progress.status = "translating"
        if on_progress:
            on_progress(self.progress)

        batches = self.batcher.create_batches(lines)
        self.progress.total_batches = len(batches)

        all_translated = []

        for batch in batches:
            if cancel_event and cancel_event.is_set():
                self.progress.status = "cancelled"
                if on_progress:
                    on_progress(self.progress)
                return original_texts[:len(all_translated)] + [""] * (len(original_texts) - len(all_translated))

            batch_start = time.perf_counter()
            try:
                translated = self.nllb.translate_batch(
                    batch.original_texts, source_lang, target_lang,
                    num_beams=num_beams, engine_batch_size=engine_batch_size,
                    device=device,
                )
                all_translated.extend(translated)
            except Exception as e:
                logger.error(f"Batch {batch.batch_index} failed: {e}")
                all_translated.extend(batch.original_texts)

            batch_elapsed = time.perf_counter() - batch_start

            self.progress.completed_batches += 1
            self.progress.completed_lines = len(all_translated)
            self.progress.last_batch_seconds = round(batch_elapsed, 2)
            self.progress.device_used = self.nllb.device

            if on_progress:
                on_progress(self.progress)

        while len(all_translated) < len(original_texts):
            all_translated.append("")
        all_translated = all_translated[:len(original_texts)]

        if glossary:
            all_translated = [glossary.restore(t) for t in all_translated]

        self.progress.status = "completed"
        if on_progress:
            on_progress(self.progress)

        return all_translated
