"""Lokalne rozpoznawanie mowy (Vosk) — działa w Brave bez Google Speech API."""

from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

from vosk import KaldiRecognizer, Model

MODEL_DIR_NAME = "vosk-model-small-pl-0.22"
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip"
SAMPLE_RATE = 16000

_MODEL: Model | None = None


def get_model_dir() -> Path:
    custom = os.getenv("VOSK_MODEL_PATH")
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parent.parent / "data" / "models" / MODEL_DIR_NAME


def model_is_ready() -> bool:
    model_dir = get_model_dir()
    return (model_dir / "am").exists() or (model_dir / "graph").exists()


def download_model() -> Path:
    models_root = get_model_dir().parent
    models_root.mkdir(parents=True, exist_ok=True)
    zip_path = models_root / f"{MODEL_DIR_NAME}.zip"

    if not zip_path.exists():
        print(f"[vosk] Pobieram model PL (~50 MB): {MODEL_URL}")
        urlretrieve(MODEL_URL, zip_path)

    if not model_is_ready():
        print(f"[vosk] Rozpakowuję {zip_path.name}...")
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(models_root)

    if not model_is_ready():
        raise RuntimeError("Nie udało się przygotować modelu Vosk.")

    return get_model_dir()


def get_vosk_model() -> Model:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    if not model_is_ready():
        download_model()

    _MODEL = Model(str(get_model_dir()))
    return _MODEL


def create_recognizer() -> KaldiRecognizer:
    """Tworzy rozpoznawacz Vosk. Gramatyka jest opcjonalna (stare wersje vosk na Mac jej nie maja)."""
    recognizer = KaldiRecognizer(get_vosk_model(), SAMPLE_RATE)

    grammar_words = [
        "panel",
        "analiza",
        "analize",
        "start",
        "stop",
        "rozpocznij",
        "zatrzymaj",
        "begin",
        "end",
        "[unk]",
    ]
    grammar_json = json.dumps(grammar_words, ensure_ascii=True)

    try:
        recognizer.SetGrammar(grammar_json)
    except (AttributeError, OSError, Exception):
        # np. symbol vosk_recognizer_set_grm not found w starszym libvosk na macOS
        pass

    return recognizer


def parse_result(payload: str, key: str) -> str:
    try:
        data = json.loads(payload)
        return (data.get(key) or "").strip()
    except json.JSONDecodeError:
        return ""
