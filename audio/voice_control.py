"""
Komunikaty głosowe trenera (TTS).

Domyślnie: Microsoft Edge TTS (polski głos neuralny, działa bez kluczy API).
Głosy Ivona (Ewa, Maja, Jacek): ustaw TTS_ENGINE=polly oraz AWS credentials.
"""

from __future__ import annotations

import asyncio
import os
import queue
import re
import subprocess
import sys
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path

# Tekst wyświetlany w UI -> wersja do odczytu na głos (lepsza wymowa Ivona/PL)
SPEAK_TEXT_MAP = {
    "Ugnij kolana!": "Ugnij kolana!",
    "Zlacz dlonie!": "Złącz dłonie!",
    "Wyprostuj lokcie!": "Wyprostuj łokcie!",
    "IDEALNE ODBICIE!": "Idealne odbicie!",
    "Nie wykryto sylwetki": "Nie wykryto sylwetki.",
    "Brak kluczowych punktów szkieletu": "Brak kluczowych punktów szkieletu.",
}

# Komunikaty, które mają być czytane na głos (pominięcie szumu statusowego)
SPEAKABLE_HINTS = (
    "Ugnij kolana!",
    "Zlacz dlonie!",
    "Wyprostuj lokcie!",
    "IDEALNE ODBICIE!",
)

AUDIO_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "audio" / "cache"
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def text_for_speech(raw: str | None) -> str | None:
    if not raw:
        return None
    parts = [part.strip() for part in raw.split("|") if part.strip()]
    if not parts:
        return None
    spoken_parts = [SPEAK_TEXT_MAP.get(part, part) for part in parts]
    return ". ".join(spoken_parts)


def extract_hints(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [hint for hint in SPEAKABLE_HINTS if hint in raw]


def new_hints(old_raw: str | None, new_raw: str | None) -> list[str]:
    old_set = set(extract_hints(old_raw))
    return [hint for hint in extract_hints(new_raw) if hint not in old_set]


class TTSBackend(ABC):
    @abstractmethod
    def synthesize(self, text: str, cache_key: str) -> Path:
        raise NotImplementedError


class EdgeTTSBackend(TTSBackend):
    def __init__(self, voice: str):
        self.voice = voice

    def synthesize(self, text: str, cache_key: str) -> Path:
        import edge_tts

        output_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

        async def _run() -> None:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))

        asyncio.run(_run())
        return output_path


class PollyBackend(TTSBackend):
    """Amazon Polly – głosy Ewa/Maja/Jacek pochodzą z technologii Ivona."""

    IVONA_VOICES = {"Ewa", "Maja", "Jacek", "Jan"}

    def __init__(self, voice: str):
        self.voice = voice if voice in self.IVONA_VOICES else "Ewa"

    def synthesize(self, text: str, cache_key: str) -> Path:
        import boto3

        output_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"
        client = boto3.client("polly")
        response = client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId=self.voice,
            LanguageCode="pl-PL",
            Engine="neural" if self.voice in {"Ewa", "Maja"} else "standard",
        )
        with open(output_path, "wb") as audio_file:
            audio_file.write(response["AudioStream"].read())
        return output_path


class Pyttsx3Backend(TTSBackend):
    def synthesize(self, text: str, cache_key: str) -> Path:
        import pyttsx3

        output_path = AUDIO_CACHE_DIR / f"{cache_key}.wav"
        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        return output_path


def _build_backend() -> TTSBackend:
    engine = os.getenv("TTS_ENGINE", "edge").strip().lower()

    if engine in {"polly", "ivona"}:
        voice = os.getenv("TTS_VOICE", "Ewa").strip()
        return PollyBackend(voice)

    if engine == "pyttsx3":
        return Pyttsx3Backend()

    voice = os.getenv("TTS_VOICE", "pl-PL-ZofiaNeural")
    return EdgeTTSBackend(voice)


def _play_audio(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.run(["afplay", str(path)], check=False)
        return

    if sys.platform.startswith("win"):
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
        return

    for player in ("mpg123", "ffplay", "aplay"):
        try:
            subprocess.run([player, str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


def _cache_key(text: str, voice_label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower())[:80]
    return f"{voice_label}_{slug}"


class CoachVoiceAnnouncer:
    def __init__(self) -> None:
        self.enabled = os.getenv("VOICE_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.cooldown_sec = float(os.getenv("VOICE_COOLDOWN_SEC", "5"))
        self.backend = _build_backend()
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._last_spoken_at = 0.0
        self._last_spoken_text: str | None = None
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="coach-voice")
        self._worker.start()

    def handle_metrics_change(
        self,
        old_posture: str | None,
        new_posture: str | None,
        old_contact: str | None,
        new_contact: str | None,
        is_analyzing: bool,
    ) -> None:
        if not self.enabled or not is_analyzing:
            return

        if new_contact and new_contact != old_contact:
            hints = new_hints(old_contact, new_contact)
            if not hints and "IDEALNE ODBICIE!" in (new_contact or ""):
                hints = ["IDEALNE ODBICIE!"]
            for hint in hints or ([new_contact] if new_contact else []):
                self._enqueue_hint(hint)
            return

        if new_posture and new_posture != old_posture:
            for hint in new_hints(old_posture, new_posture):
                self._enqueue_hint(hint)

    def _enqueue_hint(self, hint: str) -> None:
        spoken = text_for_speech(hint)
        if not spoken:
            return
        self._queue.put(spoken)

    def _worker_loop(self) -> None:
        while True:
            text = self._queue.get()
            if text is None:
                break
            try:
                self._speak_now(text)
            except Exception as error:
                print(f"[voice] Nie udało się odtworzyć komunikatu: {error}")
            finally:
                self._queue.task_done()

    def _speak_now(self, text: str) -> None:
        now = time.monotonic()
        if text == self._last_spoken_text and (now - self._last_spoken_at) < self.cooldown_sec:
            return

        voice_label = os.getenv("TTS_ENGINE", "edge")
        cache_key = _cache_key(text, voice_label)
        audio_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"
        if not audio_path.exists():
            wav_candidate = AUDIO_CACHE_DIR / f"{cache_key}.wav"
            if wav_candidate.exists():
                audio_path = wav_candidate
            else:
                audio_path = self.backend.synthesize(text, cache_key)

        _play_audio(audio_path)
        self._last_spoken_text = text
        self._last_spoken_at = time.monotonic()


_announcer: CoachVoiceAnnouncer | None = None


def get_announcer() -> CoachVoiceAnnouncer:
    global _announcer
    if _announcer is None:
        _announcer = CoachVoiceAnnouncer()
    return _announcer
