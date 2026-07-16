# Subtitle Translator

Context-aware subtitle translation web app. Translates SRT/ASS/SSA/VTT files using NLLB-200 (100% offline, no API).

## Features

- **NLLB-200-distilled-1.3B** — Meta's neural machine translation (200 languages)
- **CPU + GPU** — auto-detect CUDA, fallback to CPU
- **Multi-file batch upload** — translate multiple files in one go, download as ZIP
- **ASS/SSA tag preservation** — italic, bold, positioning tags survive translation
- **Auto-close tags** — unclosed `{\i1}` gets `{\i0}` appended automatically
- **Context batch** — groups subtitle lines for coherent NMT translation
- **Glossary** — define terms for consistent translation
- **Cancel translation** — stop in-progress translation between batches
- **Translation history** — SQLite-backed, re-download or delete past translations
- **Progress tracking** — elapsed time, ETA, lines/s, batch progress
- **Settings guide** — collapsible guide explaining Engine Batch, Num Beams, Context Batch
- **Original filename** on download

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Open `http://localhost:8000`

## Configuration

### UI Settings

| Setting | Default | Options | Description |
|---------|---------|---------|-------------|
| Device | Auto | Auto / CPU / GPU (CUDA) | Hardware selection |
| Num Beams | 2 (Fast) | 2 / 3 / 4 | Search width per line |
| Engine Batch | 8 (Default) | 4 / 8 / 16 / 32 / 64 | Lines per NMT model call |
| Context Batch | 15 | 5–50 | Lines grouped for context |

> **Engine Batch note**: For subtitle text (short sequences), 4–8 is fastest. Larger batches (16–64) are only faster for long-form text (documents, articles) on GPUs with 12GB+ VRAM.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NLLB_MODEL` | `facebook/nllb-200-distilled-1.3B` | HuggingFace model ID or local path |
| `BATCH_SIZE` | `15` | Default context batch size |
| `MAX_LINE_LENGTH` | `42` | Max characters per subtitle line |
| `DEVICE` | `auto` | `auto`, `cpu`, or `cuda` |

### Local Model Path (no re-download)

Set env var to a local directory:

```bash
set NLLB_MODEL=D:\Models\nllb-200-distilled-1.3B
```

Or edit `app/config.py` directly.

## Supported Formats

| Format | Extensions | Tag Support |
|--------|-----------|-------------|
| SubStation Alpha | `.ass`, `.ssa` | `{\i1}`, `{\b1}`, `{\pos}`, etc. |
| SubRip | `.srt` | Plain text |
| WebVTT | `.vtt` | Plain text |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/translate` | POST | Translate single file |
| `/api/translate-batch` | POST | Translate multiple files |
| `/api/progress/{id}` | GET | Translation progress (poll) |
| `/api/cancel/{id}` | POST | Cancel in-progress translation |
| `/api/download/{id}` | GET | Download single translated file |
| `/api/download-batch/{id}` | GET | Download batch as ZIP |
| `/api/languages` | GET | Supported language list |
| `/api/device-info` | GET | CUDA/GPU detection |
| `/api/history` | GET | Translation history (50 latest) |
| `/api/history/{id}/download` | GET | Re-download from history |
| `/api/history/{id}` | DELETE | Delete history entry + files |

## Project Structure

```
Translate/
  app/
    main.py              # FastAPI entry point, startup init
    config.py            # Model config, language maps
    db.py                # SQLite history layer (init, CRUD)
    api/
      routes.py          # REST endpoints
      models.py          # Pydantic models
    translator/
      nllb_engine.py     # NLLB-200 translation engine
      pipeline.py        # Translation orchestrator
      parser.py          # Subtitle file parser (SRT/ASS/VTT)
      context_batcher.py # Context-aware batching
      glossary.py        # Custom glossary
      argos_engine.py    # Argos Translate fallback
      ner.py             # Named entity recognition (disabled)
      postprocess.py     # Post-processing (unused)
    static/
      index.html         # Web UI
      style.css          # Dark theme
      app.js             # Frontend logic
  data.db                # SQLite database (auto-created)
  uploads/               # Uploaded subtitle files
  output/                # Translated output files
  run.py                 # python run.py → localhost:8000
  requirements.txt
  sample_en.srt          # Sample file for testing
```

## Tech Stack

- **NMT**: [NLLB-200](https://github.com/facebookresearch/fairseq/tree/nllb) (Meta) via HuggingFace Transformers
- **Backend**: FastAPI + uvicorn
- **Subtitle parsing**: pysubs2
- **GPU acceleration**: PyTorch + CUDA (optional)
- **History**: SQLite (built-in, no extra dependency)

## License

MIT
