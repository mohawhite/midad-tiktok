"""Récupération du texte, de la traduction et de l'audio, verset par verset."""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import requests

ALQURAN = "https://api.alquran.cloud/v1"
QURANCOM = "https://api.quran.com/api/v4"
CACHE = Path(".cache")
SANS_BASMALA = (1, 9)  # Al-Fatiha : c'est le verset 1 ; At-Tawba : aucune basmala


class SourceError(RuntimeError):
    """Une source ne répond pas ou renvoie des données incohérentes."""


def _get(url: str, *, binary: bool = False, tries: int = 4) -> bytes:
    delay = 2
    last: Exception | None = None
    for attempt in range(tries + 1):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                return r.content
            last = SourceError(f"HTTP {r.status_code} pour {url}")
        except requests.RequestException as exc:  # réseau
            last = exc
        if attempt < tries:
            time.sleep(delay)
            delay *= 2
    raise SourceError(f"Échec après {tries + 1} essais : {url} ({last})")


def get_json(url: str) -> dict:
    CACHE.mkdir(exist_ok=True)
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = json.loads(_get(url))
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def skeleton(text: str) -> str:
    """Squelette consonantique : sert uniquement à comparer deux sources.

    Les éditions Uthmani diffèrent par leurs signes (voyelles, petits alifs,
    marques de pause) mais jamais par leurs lettres.
    """
    out = []
    for ch in unicodedata.normalize("NFD", text):
        if unicodedata.category(ch) in ("Mn", "Cf") or ch == "ـ":
            continue
        if "ۖ" <= ch <= "ۭ":  # marques de pause et annotations coraniques
            continue
        if ch in "ٱأإآ":  # variantes d'alif
            ch = "ا"
        elif ch == "ى":  # alif maqsura / ya sans points
            ch = "ي"
        out.append(ch)
    return "".join("".join(out).split())


@dataclass
class Verse:
    surah: int
    number: int  # 0 = basmala affichée avant le verset 1
    arabic: str
    french: str
    audio_url: str
    audio_path: Path | None = None
    duration: float = 0.0

    @property
    def key(self) -> str:
        return f"{self.surah}:{self.number}"


@dataclass
class Surah:
    number: int
    name_arabic: str
    name_latin: str
    verses_count: int
    verses: list[Verse] = field(default_factory=list)


def load_surah(number: int, reciter: str, translation: str, names: dict | None = None) -> Surah:
    """Charge une sourate entière et contrôle le texte contre Quran.com."""
    data = get_json(f"{ALQURAN}/surah/{number}/editions/quran-uthmani,{translation},{reciter}")["data"]
    by_id = {e["edition"]["identifier"]: e for e in data}
    ar, fr, au = by_id["quran-uthmani"], by_id[translation], by_id[reciter]
    chapter = get_json(f"{QURANCOM}/chapters/{number}?language=fr")["chapter"]
    check = get_json(
        f"{QURANCOM}/verses/by_chapter/{number}?fields=text_uthmani&per_page=300&words=false"
    )["verses"]

    count = chapter["verses_count"]
    if not (len(ar["ayahs"]) == len(fr["ayahs"]) == len(au["ayahs"]) == len(check) == count):
        raise SourceError(f"Sourate {number} : nombre de versets incohérent entre les sources")

    basmala = get_json(f"{ALQURAN}/ayah/1:1/editions/quran-uthmani,{translation},{reciter}")["data"]
    b_ar, b_fr, b_au = basmala[0]["text"], basmala[1]["text"], basmala[2]["audio"]

    surah = Surah(
        number=number,
        name_arabic=chapter["name_arabic"],
        name_latin=(names or {}).get(number) or chapter["name_simple"],
        verses_count=count,
    )
    for a, f, u, c in zip(ar["ayahs"], fr["ayahs"], au["ayahs"], check):
        n = a["numberInSurah"]
        if not (n == f["numberInSurah"] == u["numberInSurah"] == c["verse_number"]):
            raise SourceError(f"Sourate {number} : numérotation incohérente au verset {n}")
        text = a["text"].strip()
        if n == 1 and number not in SANS_BASMALA:
            # Le texte d'alquran.cloud inclut la basmala, pas le fichier audio.
            words = text.split(" ")
            if skeleton(" ".join(words[:4])) != skeleton(b_ar):
                raise SourceError(f"Sourate {number} : basmala attendue au début du verset 1")
            text = " ".join(words[4:])
            surah.verses.append(Verse(number, 0, b_ar, b_fr.strip(), b_au))
        if skeleton(text) != skeleton(c["text_uthmani"]):
            raise SourceError(f"Verset {number}:{n} : le texte diffère entre alquran.cloud et Quran.com")
        surah.verses.append(Verse(number, n, text, f["text"].strip(), u["audio"]))
    return surah


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return float(out)


def fetch_audio(verses: list[Verse], reciter: str) -> None:
    """Télécharge chaque verset et le convertit en WAV pour un minutage exact."""
    folder = CACHE / "audio" / reciter
    folder.mkdir(parents=True, exist_ok=True)
    for v in verses:
        stem = "basmala" if v.number == 0 else f"{v.surah:03d}{v.number:03d}"
        mp3, wav = folder / f"{stem}.mp3", folder / f"{stem}.wav"
        if not mp3.exists():
            mp3.write_bytes(_get(v.audio_url, binary=True))
        if not wav.exists():
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", str(mp3), "-ar", "44100", "-ac", "2", str(wav)],
                check=True,
            )
        v.audio_path, v.duration = wav, probe_duration(wav)
        if v.duration < 0.5:
            raise SourceError(f"Verset {v.key} : fichier audio vide ou trop court")
