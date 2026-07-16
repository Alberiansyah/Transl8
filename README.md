# Subtitle Translator

Context-aware subtitle translation web app. Translates SRT/ASS/SSA/VTT files using NLLB-200 (100% offline, no API).

## Features

- **NLLB-200-distilled-1.3B** — Meta's neural machine translation (200 languages)
- **CPU + GPU** — auto-detect CUDA, fallback to CPU
- **ASS/SSA tag preservation** — italic, bold, positioning tags survive translation
- **Auto-close tags** — unclosed `{\i1}` gets `{\i0}` appended automatically
- **Context batch** — groups subtitle lines for coherent NMT translation
- **Glossary** — define terms for consistent translation
- **Progress tracking** — real-time elapsed time, lines/s, batch progress
- **Original filename** on download

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

Open `http://localhost:8000`

## Configuration

### UI Settings

| Setting | CPU Default | GPU Default | Description |
|---------|-------------|-------------|-------------|
| Device | Auto | Auto | CPU / GPU (CUDA) / Auto |
| Num Beams | 2 | 2 | Search width (2=fast, 4=quality) |
| Engine Batch | 8 | 8 | Lines per NMT batch |
| Context Batch | 15 | 15 | Lines per context group |

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

## Project Structure

```
Translate/
  app/
    main.py              # FastAPI entry point
    config.py            # Model config, language maps
    api/
      routes.py          # API endpoints
      models.py          # Pydantic models
    translator/
      nllb_engine.py     # NLLB-200 translation engine
      pipeline.py        # Translation orchestrator
      parser.py          # Subtitle file parser (SRT/ASS/VTT)
      context_batcher.py # Context-aware batching
      glossary.py        # Custom glossary
      argos_engine.py    # Argos Translate fallback
      ner.py             # Named entity recognition
      postprocess.py     # Post-processing
    static/
      index.html         # Web UI
      style.css          # Dark theme
      app.js             # Frontend logic
  run.py                 # python run.py → localhost:8000
  requirements.txt
  sample_en.srt          # Sample file for testing
```

## Tech Stack

- **NMT**: [NLLB-200](https://github.com/facebookresearch/fairseq/tree/nllb) (Meta) via HuggingFace Transformers
- **Backend**: FastAPI + uvicorn
- **Subtitle parsing**: pysubs2
- **GPU acceleration**: PyTorch + CUDA (optional)
- **Fallback**: Argos Translate

## License

MIT
