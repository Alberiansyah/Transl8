from __future__ import annotations

import uuid
import threading
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.config import UPLOAD_DIR, OUTPUT_DIR, NLLB_LANG_MAP
from app.api.models import (
    TranslateRequest, TranslateResponse, ProgressResponse,
    LanguageInfo, FileInfo,
)
from app.translator.parser import load_subtitle, save_subtitle
from app.translator.pipeline import TranslationPipeline, TranslationProgress
from app.translator.glossary import Glossary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

jobs: dict[str, dict] = {}
pipeline = TranslationPipeline()


@router.get("/languages", response_model=list[LanguageInfo])
async def get_languages():
    common = [
        ("en", "English"), ("id", "Indonesian"), ("ms", "Malay"),
        ("ja", "Japanese"), ("ko", "Korean"), ("zh", "Chinese"),
        ("th", "Thai"), ("vi", "Vietnamese"), ("tl", "Filipino"),
        ("ar", "Arabic"), ("hi", "Hindi"), ("bn", "Bengali"),
        ("pt", "Portuguese"), ("es", "Spanish"), ("fr", "French"),
        ("de", "German"), ("it", "Italian"), ("ru", "Russian"),
        ("tr", "Turkish"), ("pl", "Polish"), ("nl", "Dutch"),
        ("sv", "Swedish"), ("no", "Norwegian"), ("da", "Danish"),
        ("fi", "Finnish"), ("cs", "Czech"), ("sk", "Slovak"),
        ("hu", "Hungarian"), ("ro", "Romanian"), ("bg", "Bulgarian"),
        ("hr", "Croatian"), ("sr", "Serbian"), ("uk", "Ukrainian"),
        ("el", "Greek"), ("he", "Hebrew"), ("fa", "Persian"),
        ("sw", "Swahili"), ("ta", "Tamil"), ("te", "Telugu"),
        ("ml", "Malayalam"), ("my", "Myanmar"), ("km", "Khmer"),
        ("lo", "Lao"), ("ka", "Georgian"), ("am", "Amharic"),
        ("ne", "Nepali"), ("si", "Sinhala"), ("ur", "Urdu"),
    ]
    return [LanguageInfo(code=c, name=n) for c, n in common]


@router.get("/device-info")
async def get_device_info():
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            return {
                "cuda_available": True,
                "gpu_name": torch.cuda.get_device_name(0),
                "cuda_version": torch.version.cuda,
                "pytorch_version": torch.__version__,
            }
        return {
            "cuda_available": False,
            "gpu_name": None,
            "cuda_version": None,
            "pytorch_version": torch.__version__,
        }
    except ImportError:
        return {
            "cuda_available": False,
            "gpu_name": None,
            "cuda_version": None,
            "pytorch_version": None,
        }


@router.post("/upload", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".srt", ".ass", ".ssa", ".vtt"):
        raise HTTPException(400, f"Unsupported format: {ext}. Use SRT, ASS, SSA, or VTT.")

    file_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{file_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    try:
        sub_data = load_subtitle(save_path)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse subtitle: {e}")

    return FileInfo(
        filename=file.filename,
        format=ext.lstrip("."),
        line_count=sub_data.line_count,
    )


@router.post("/translate", response_model=TranslateResponse)
async def start_translation(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_lang: str = Form("id"),
    batch_size: int = Form(15),
    num_beams: int = Form(3),
    engine_batch_size: int = Form(16),
    device: str = Form("auto"),
    glossary: str = Form("[]"),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in (".srt", ".ass", ".ssa", ".vtt"):
        raise HTTPException(400, f"Unsupported format: {ext}")

    job_id = str(uuid.uuid4())[:8]
    save_path = UPLOAD_DIR / f"{job_id}{ext}"
    output_path = OUTPUT_DIR / f"{job_id}_translated{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    try:
        sub_data = load_subtitle(save_path)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse subtitle: {e}")

    import json
    try:
        glossary_data = json.loads(glossary) if glossary else []
    except json.JSONDecodeError:
        glossary_data = []

    gl = Glossary.from_dict(glossary_data) if glossary_data else None

    jobs[job_id] = {
        "progress": TranslationProgress(status="queued"),
        "sub_data": sub_data,
        "output_path": str(output_path),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "batch_size": batch_size,
        "num_beams": num_beams,
        "engine_batch_size": engine_batch_size,
        "device": device,
        "glossary": gl,
        "original_filename": file.filename,
    }

    thread = threading.Thread(target=_run_translation, args=(job_id,), daemon=True)
    thread.start()

    return TranslateResponse(
        job_id=job_id,
        status="queued",
        message=f"Translation started: {file.filename} ({source_lang} -> {target_lang})",
    )


def _run_translation(job_id: str):
    job = jobs[job_id]

    def on_progress(progress: TranslationProgress):
        job["progress"] = progress

    try:
        final_texts = pipeline.translate(
            sub_file=job["sub_data"],
            source_lang=job["source_lang"],
            target_lang=job["target_lang"],
            glossary=job["glossary"],
            batch_size=job["batch_size"],
            num_beams=job["num_beams"],
            engine_batch_size=job["engine_batch_size"],
            device=job["device"],
            on_progress=on_progress,
        )

        save_subtitle(job["sub_data"], final_texts, job["output_path"])

    except Exception as e:
        logger.error(f"Translation job {job_id} failed: {e}")
        job["progress"] = TranslationProgress(status="failed", error=str(e))


@router.get("/progress/{job_id}", response_model=ProgressResponse)
async def get_progress(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    progress = jobs[job_id]["progress"]
    return ProgressResponse(
        job_id=job_id,
        status=progress.status,
        percent=progress.percent,
        total_batches=progress.total_batches,
        completed_batches=progress.completed_batches,
        error=progress.error,
        elapsed_seconds=progress.elapsed_seconds,
        last_batch_seconds=progress.last_batch_seconds,
        device_used=progress.device_used,
        lines_per_second=progress.lines_per_second,
    )


@router.get("/download/{job_id}")
async def download_translation(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Job not found")

    job = jobs[job_id]
    output_path = Path(job["output_path"])

    if not output_path.exists():
        raise HTTPException(404, "Translated file not ready yet")

    original_name = Path(job.get("original_filename", output_path.name)).stem
    ext = output_path.suffix

    return FileResponse(
        path=str(output_path),
        filename=f"{original_name}{ext}",
        media_type="application/octet-stream",
    )
