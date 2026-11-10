"""Contrôle par reconnaissance vocale : l'audio dit-il bien le verset affiché ?"""
from __future__ import annotations

import difflib
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from .sources import Verse, skeleton

MODELE = "OdyAsh/faster-whisper-base-ar-quran"  # Whisper « base » affiné sur la récitation du Coran


@lru_cache(maxsize=1)
def _modele():
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from faster_whisper import WhisperModel
    return WhisperModel(MODELE, device="cpu", compute_type="int8")


def _charger_audio(path: Path):
    """Décode en mono 16 kHz avec FFmpeg, le format attendu par le modèle."""
    import numpy as np
    brut = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                          check=True, capture_output=True).stdout
    return np.frombuffer(brut, dtype=np.float32)


def transcrire(path: Path) -> str:
    """Transcrit par fenêtres de 25 s : le modèle n'entend que 30 s à la fois."""
    audio, pas, textes = _charger_audio(path), 25 * 16000, []
    for i in range(0, len(audio), pas):
        segments, _ = _modele().transcribe(audio[i:i + pas], language="ar", beam_size=5,
                                           condition_on_previous_text=False)
        textes.append(" ".join(s.text for s in segments))
    return " ".join(textes)


def ressemblance(entendu: str, attendu: str) -> float:
    return difflib.SequenceMatcher(None, skeleton(entendu), skeleton(attendu), autojunk=False).ratio()


def controler(verses: list[Verse], seuil: float) -> list[str]:
    """Renvoie la liste des versets dont l'audio ne ressemble pas assez au texte."""
    problemes = []
    for v in verses:
        score = ressemblance(transcrire(v.audio_path), v.arabic)
        if score < seuil:
            problemes.append(f"{v.key} : l'audio ne correspond pas assez au texte (ressemblance {score:.2f})")
    return problemes
