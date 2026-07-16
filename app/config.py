import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

NLLB_MODEL = os.getenv("NLLB_MODEL", "facebook/nllb-200-distilled-1.3B")
SPACY_MODEL = os.getenv("SPACY_MODEL", "xx_ent_wiki_sm")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "15"))
MAX_LINE_LENGTH = int(os.getenv("MAX_LINE_LENGTH", "42"))
DEVICE = os.getenv("DEVICE", "auto")

NLLB_LANG_MAP = {
    "en": "eng_Latn", "id": "ind_Latn", "ms": "zsm_Latn",
    "ja": "jpn_Jpan", "ko": "kor_Hang", "zh": "cmn_Hans",
    "th": "tha_Thai", "vi": "vie_Latn", "tl": "tgl_Latn",
    "ar": "arb_Arab", "hi": "hin_Deva", "bn": "ben_Beng",
    "pt": "por_Latn", "es": "spa_Latn", "fr": "fra_Latn",
    "de": "deu_Latn", "it": "ita_Latn", "ru": "rus_Cyrl",
    "tr": "tur_Latn", "pl": "pol_Latn", "nl": "nld_Latn",
    "sv": "swe_Latn", "no": "nob_Latn", "da": "dan_Latn",
    "fi": "fin_Latn", "cs": "ces_Latn", "sk": "slk_Latn",
    "hu": "hun_Latn", "ro": "ron_Latn", "bg": "bul_Cyrl",
    "hr": "hrv_Latn", "sr": "srp_Cyrl", "uk": "ukr_Cyrl",
    "el": "ell_Grek", "he": "heb_Hebr", "fa": "pes_Arab",
    "sw": "swh_Latn", "ta": "tam_Taml", "te": "tel_Telu",
    "ml": "mal_Mlym", "my": "mya_Mymr", "km": "khm_Khmr",
    "lo": "lao_Laoo", "ka": "kat_Geor", "am": "amh_Ethi",
    "ne": "npi_Deva", "si": "sin_Sinh", "ur": "urd_Arab",
}

NLLB_LANG_MAP_REVERSE = {v: k for k, v in NLLB_LANG_MAP.items()}
