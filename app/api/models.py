from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class TranslateRequest(BaseModel):
    source_lang: str = "en"
    target_lang: str = "id"
    use_ner: bool = True
    batch_size: int = 15
    glossary: list[dict] = []


class GlossaryEntryModel(BaseModel):
    source: str
    target: str
    case_sensitive: bool = True


class TranslateResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ProgressResponse(BaseModel):
    job_id: str
    status: str
    percent: float
    total_batches: int
    completed_batches: int
    error: Optional[str] = None
    elapsed_seconds: float = 0.0
    last_batch_seconds: float = 0.0
    device_used: str = "cpu"
    lines_per_second: float = 0.0


class LanguageInfo(BaseModel):
    code: str
    name: str


class FileInfo(BaseModel):
    filename: str
    format: str
    line_count: int
    detected_source: Optional[str] = None
