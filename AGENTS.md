# AGENTS.md

## Project

Subtitle Translator — context-aware NMT subtitle translation web app.

## Run

```bash
python run.py
# → http://localhost:8000
```

## Architecture

- `app/main.py` — FastAPI app, mounts static files, serves index, calls `init_db()` on startup
- `app/config.py` — NLLB model path, language map (code → NLLB code like `eng_Latn`), env vars
- `app/db.py` — SQLite layer: `init_db()`, `save_history()`, `get_history()`, `get_history_entry()`, `delete_history()`. DB file: `data.db` at project root.
- `app/api/routes.py` — REST endpoints (see API below)
- `app/api/models.py` — Pydantic models: `TranslateResponse`, `ProgressResponse`, `HistoryEntry`, `LanguageInfo`, `FileInfo`
- `app/translator/nllb_engine.py` — Core NMT: loads `facebook/nllb-200-distilled-1.3B` via `transformers`, handles CPU/CUDA, `torch.compile()` for GPU, warmup on first load. Returns `list[str]`.
- `app/translator/pipeline.py` — Orchestrator: splits lines into context batches via `ContextBatcher`, calls `NLLBEngine.translate_batch()` per batch, tracks `completed_lines`. Supports `cancel_event: threading.Event`. `TranslationPipeline.translate()` is the main entry.
- `app/translator/parser.py` — `load_subtitle()` / `save_subtitle()` using pysubs2. For ASS/SSA: extracts `{\...}` tags (prefix/suffix/unclosed) and restores them to translated output.
- `app/translator/context_batcher.py` — Groups `SubtitleLine`s into `Batch` objects. Non-overlapping. Each batch has `original_texts` list.
- `app/translator/glossary.py` — `Glossary` class: uses placeholders `GLOSSARY_N` during translation, restores after.
- `app/translator/ner.py` — spaCy NER (disabled in pipeline — NLLB corrupts placeholder text with entity names).
- `app/translator/postprocess.py` — Tag restoration, line length fixing, punctuation cleanup. Currently not called in pipeline.
- `app/static/` — index.html, style.css (dark theme), app.js

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/translate` | POST | Translate single file (multipart form) |
| `/api/translate-batch` | POST | Translate multiple files (multipart form) |
| `/api/progress/{id}` | GET | Translation progress (poll every 800ms) |
| `/api/cancel/{id}` | POST | Cancel in-progress translation |
| `/api/download/{id}` | GET | Download single translated file |
| `/api/download-batch/{id}` | GET | Download batch as ZIP |
| `/api/languages` | GET | Supported language list |
| `/api/device-info` | GET | CUDA/GPU detection |
| `/api/history` | GET | Translation history (50 latest, newest first) |
| `/api/history/{id}/download` | GET | Re-download from history (file or ZIP) |
| `/api/history/{id}` | DELETE | Delete history entry + output files |

## Key Design Decisions

1. **Model loading is singleton** — `pipeline = TranslationPipeline()` at module level in routes.py. `NLLBEngine.load_model()` reloads only if device changes.
2. **Device switching** — If user switches CPU→GPU or vice versa, model is unloaded (`del self.model`, `torch.cuda.empty_cache()`) and reloaded to new device.
3. **ASS tag preservation** — `parser.py:extract_tags()` extracts prefix/suffix/auto-close tags. `save_subtitle()` reconstructs: `prefix + translated + auto_close + suffix`.
4. **Context batching** — Lines are grouped into batches (default 15). Each batch is translated as a group. No overlap between batches.
5. **Engine batch** — Within each context batch, lines are further chunked by `engine_batch_size` for the NMT model.
6. **GPU optimization** — For 1.3B model, small engine_batch (8) is faster than large (64) due to padding overhead with short subtitle text.
7. **NER disabled** — Entity replacement with `ENTX_0` placeholders gets corrupted by NLLB (e.g., "Sarah" → "James Bond0").
8. **Timing computed at read-time** — `elapsed_seconds`, `lines_per_second`, `eta_seconds` are computed in `/api/progress` endpoint using `time.time() - job["start_time"]`, NOT written by the pipeline thread. Eliminates race condition timing jumps.
9. **Cancel via threading.Event** — `cancel_event` is passed to `pipeline.translate()`. Checked between context batches. Max wait ~1-2s.
10. **History in SQLite** — Auto-saved on translation completion. In-memory `jobs` dict for active translations, `data.db` for completed history.

## Common Tasks

### Add new API endpoint
1. Define Pydantic model in `app/api/models.py`
2. Add route in `app/api/routes.py`
3. Frontend: add fetch call in `app/static/app.js`

### Add new language
Add to `NLLB_LANG_MAP` in `app/config.py` with correct NLLB code from [NLLB docs](https://github.com/facebookresearch/fairseq/tree/nllb). Also add to `LANG_NAMES` dict in `app/api/routes.py` and `app/static/app.js`.

### Change default settings
Edit `DEVICE_PRESETS` in `app/static/app.js` for UI defaults.
Edit `app/config.py` for backend defaults.

### Debug translation issues
Check server logs — `nllb_engine.py` logs each batch: `Translated X lines in Y.ZZZs (device)`.

## Testing

No test framework set up. Manual testing:
1. Upload `sample_en.srt` via web UI
2. Translate en→id
3. Check download output
4. Verify history entry appears after completion

For ASS tag testing, create a `.ass` file with `{\i1}`, `{\b1}` tags and verify they survive translation.

## Environment

- Python 3.14
- PyTorch 2.11.0+cu128 (CUDA) or CPU
- No CUDA toolkit required for CPU mode
- Model: `facebook/nllb-200-distilled-1.3B` (~10GB, cached in `~/.cache/huggingface/`)
- SQLite (built-in, used for translation history)
