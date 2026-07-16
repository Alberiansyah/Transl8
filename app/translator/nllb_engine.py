from __future__ import annotations

import time
import logging
from app.config import NLLB_MODEL, NLLB_LANG_MAP

logger = logging.getLogger(__name__)


def resolve_device(requested: str) -> str:
    if requested == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                logger.info(f"CUDA available: {name}")
                return "cuda"
        except ImportError:
            pass
        return "cpu"
    if requested == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                logger.warning("CUDA requested but not available, falling back to CPU")
                return "cpu"
        except ImportError:
            return "cpu"
    return requested


class NLLBEngine:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.model_loaded = False
        self.device = "cpu"
        self._compiled = False

    def load_model(self, device: str = "auto"):
        new_device = resolve_device(device)

        if self.model_loaded and self.device == new_device:
            return

        if self.model_loaded:
            logger.info(f"Switching device: {self.device} -> {new_device}")
            import torch
            del self.model
            self.model = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            self.model_loaded = False
            self._compiled = False

        logger.info(f"Loading NLLB model: {NLLB_MODEL} (device={new_device})")

        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch

        if new_device == "cpu":
            cpu_count = torch.get_num_threads()
            torch.set_num_threads(min(cpu_count, 10))
            logger.info(f"CPU threads: {torch.get_num_threads()}")

        self.tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL)

        use_fp16 = new_device == "cuda"
        dtype = torch.float16 if use_fp16 else torch.float32
        self.model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL, torch_dtype=dtype)
        self.model = self.model.to(new_device)
        self.model.eval()
        self.device = new_device

        if new_device == "cuda" and not self._compiled:
            try:
                self.model = torch.compile(self.model, mode="reduce-overhead")
                self._compiled = True
                logger.info("Model compiled with torch.compile()")
            except Exception as e:
                logger.warning(f"torch.compile() failed (non-fatal): {e}")

        self.model_loaded = True
        logger.info(f"NLLB model loaded on {self.device}")

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        num_beams: int = 2,
        engine_batch_size: int = 16,
        device: str = "auto",
    ) -> list[str]:
        self.load_model(device)

        import torch

        src_code = NLLB_LANG_MAP.get(source_lang, source_lang)
        tgt_code = NLLB_LANG_MAP.get(target_lang, target_lang)
        tgt_token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)

        self.tokenizer.src_lang = src_code

        results = []
        for i in range(0, len(texts), engine_batch_size):
            chunk = texts[i:i + engine_batch_size]
            chunk_results = self._translate_chunk(chunk, tgt_token_id, num_beams)
            results.extend(chunk_results)

        return results

    def _translate_chunk(self, texts: list[str], tgt_token_id: int, num_beams: int) -> list[str]:
        import torch

        valid_indices = [j for j, t in enumerate(texts) if t.strip()]
        if not valid_indices:
            return [""] * len(texts)

        valid_texts = [texts[j] for j in valid_indices]

        inputs = self.tokenizer(
            valid_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        ).to(self.device)

        if self.device == "cuda":
            torch.cuda.synchronize()

        t0 = time.perf_counter()

        with torch.inference_mode():
            translated = self.model.generate(
                **inputs,
                forced_bos_token_id=tgt_token_id,
                max_length=128,
                num_beams=num_beams,
                early_stopping=True,
            )

        if self.device == "cuda":
            torch.cuda.synchronize()

        elapsed = time.perf_counter() - t0

        decoded = self.tokenizer.batch_decode(translated, skip_special_tokens=True)

        results = [""] * len(texts)
        for idx, text in zip(valid_indices, decoded):
            results[idx] = text.strip()

        logger.info(f"Translated {len(valid_texts)} lines in {elapsed:.3f}s ({self.device})")
        return results
