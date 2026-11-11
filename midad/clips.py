"""Fond vidéo : choix des clips Pexels et Pixabay, puis assemblage avec fondus enchaînés."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
import yaml

from . import layout
from .sources import CACHE, SourceError, probe_duration

FPS = 30
FONDU = 1.0          # durée du fondu enchaîné entre deux clips
CLIP_MIN, CLIP_MAX = 8.0, 20.0

# Aucun clip dont le titre ou les tags contiennent l'un de ces mots (personnes, animaux, etc.).
EXCLUS = """
person people man men woman women girl boy child children kid kids baby human humans face portrait hand hands
foot feet body silhouette couple family crowd tourist tourists hiker surfer surfing swimmer swimming diver
fisherman fishing walking running dancing yoga model bride wedding selfie
animal animals bird birds seagull seagulls eagle dove horse horses camel camels dog cat cow sheep goat deer
fish fishes dolphin whale shark turtle jellyfish insect butterfly bee bees ant spider snake lion elephant wildlife
city street car cars boat ship ships sailboat building buildings church mosque temple statue cross
drone-selfie beer wine alcohol bikini party christmas halloween
personne homme femme enfant visage main animal oiseau cheval chameau poisson
""".split()


@dataclass
class Clip:
    id: str          # par exemple « pexels:9620654 »
    auteur: str
    lien: str
    url: str         # fichier vidéo à télécharger
    duree: float


def _api(url: str, headers: dict | None = None) -> dict:
    """Appel d'API avec cache de 24 h, comme le demande Pixabay."""
    folder = CACHE / "clips_api"
    folder.mkdir(parents=True, exist_ok=True)
    sans_cle = re.sub(r"key=[^&]+", "key=", url)
    path = folder / (hashlib.sha1(sans_cle.encode()).hexdigest() + ".json")
    if path.exists() and time.time() - path.stat().st_mtime < 86400:
        return json.loads(path.read_text(encoding="utf-8"))
    delay, last = 2, ""
    for attempt in range(5):
        try:
            r = requests.get(url, headers=headers or {}, timeout=60)
            if r.status_code == 200:
                path.write_text(r.text, encoding="utf-8")
                return r.json()
            last = f"HTTP {r.status_code}"
        except requests.RequestException as exc:
            last = type(exc).__name__
        if attempt < 4:
            time.sleep(delay)
            delay *= 2
    raise SourceError(f"Recherche de clips impossible ({last}) : {sans_cle}")


def _interdit(texte: str) -> bool:
    mots = set(re.findall(r"[a-zà-ÿ]+", texte.lower()))
    return any(m in mots for m in EXCLUS)


def _pexels(mot: str) -> list[Clip]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    q = requests.utils.quote(mot)
    data = _api(f"https://api.pexels.com/videos/search?query={q}&orientation=portrait&per_page=30",
                {"Authorization": key})
    out = []
    for v in data.get("videos", []):
        slug = v["url"].rstrip("/").rsplit("/", 1)[-1]
        fichiers = [f for f in v["video_files"] if f["width"] >= 1080 and f["height"] >= 1920
                    and f["height"] > f["width"]]
        if not fichiers or v["duration"] < 6 or _interdit(slug.replace("-", " ")):
            continue
        f = min(fichiers, key=lambda f: f["width"])
        out.append(Clip(f"pexels:{v['id']}", v["user"]["name"], v["url"], f["link"], float(v["duration"])))
    return out


def _pixabay(mot: str) -> list[Clip]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    q = requests.utils.quote(mot)
    data = _api(f"https://pixabay.com/api/videos/?key={key}&q={q}&video_type=film&category=nature"
                f"&safesearch=true&min_height=1920&per_page=30")
    out = []
    for v in data.get("hits", []):
        grand = v["videos"].get("large") or {}
        # Un clip horizontal n'est gardé que s'il est assez haut pour être recadré sans perte.
        if not grand.get("url") or grand["height"] < 1920 or v["duration"] < 6 or _interdit(v["tags"]):
            continue
        out.append(Clip(f"pixabay:{v['id']}", v["user"], v["pageURL"], grand["url"], float(v["duration"])))
    return out


def plages(debuts_versets: list[float], total: float) -> list[tuple[float, float]]:
    """Découpe la vidéo en plages de fond qui ne changent qu'au début d'un verset."""
    bornes = [0.0]
    for t in debuts_versets:
        if t - bornes[-1] >= CLIP_MIN and total - t >= CLIP_MIN / 2:
            bornes.append(t)
    return list(zip(bornes, bornes[1:] + [total]))


def choisir(mots: list[str], n: int, interdits: set[str], graine: str) -> list[Clip]:
    """Choisit n clips distincts en alternant les mots-clés de la sourate."""
    exclus_fichier = Path("clips_exclus.yaml")
    bannis = set(yaml.safe_load(exclus_fichier.read_text(encoding="utf-8")) or []) if exclus_fichier.exists() else set()
    rng = random.Random(graine)
    paniers = []
    for mot in mots:
        cands = [c for c in _pexels(mot) + _pixabay(mot) if c.id not in interdits and c.id not in bannis]
        rng.shuffle(cands)
        paniers.append(cands)
    choisis: list[Clip] = []
    pris: set[str] = set()
    while len(choisis) < n and any(paniers):
        for panier in paniers:
            while panier:
                c = panier.pop()
                if c.id not in pris:
                    pris.add(c.id)
                    choisis.append(c)
                    break
            if len(choisis) == n:
                break
    if not choisis:
        raise SourceError(f"Aucun clip utilisable pour les mots-clés {mots}")
    return choisis


def _telecharger(clip: Clip) -> Path:
    folder = CACHE / "clips"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (clip.id.replace(":", "_") + ".mp4")
    if path.exists():
        return path
    delay = 2
    for attempt in range(5):
        try:
            with requests.get(clip.url, stream=True, timeout=120) as r:
                r.raise_for_status()
                tmp = path.with_suffix(".part")
                with open(tmp, "wb") as f:
                    for bloc in r.iter_content(1 << 20):
                        f.write(bloc)
                tmp.rename(path)
                return path
        except requests.RequestException:
            if attempt == 4:
                raise SourceError(f"Téléchargement impossible : {clip.lien}")
            time.sleep(delay)
            delay *= 2
    return path


def assembler(clips: list[Clip], segments: list[tuple[float, float]], work: Path) -> Path:
    """Met chaque clip au format 1080 × 1920, puis les enchaîne avec un fondu d'une seconde."""
    work.mkdir(parents=True, exist_ok=True)
    morceaux = []
    for i, (a, b) in enumerate(segments):
        clip = clips[i % len(clips)]
        src = _telecharger(clip)
        if probe_duration(src) < 1:
            raise SourceError(f"Clip illisible : {clip.lien}")
        dur = b - a + (FONDU if i < len(segments) - 1 else 0)
        out = work / f"fond_{i:02d}.mp4"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", str(src), "-t", f"{dur:.3f}", "-an",
             "-vf", f"scale={layout.W}:{layout.H}:force_original_aspect_ratio=increase,"
                    f"crop={layout.W}:{layout.H},fps={FPS},format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", str(out)], check=True)
        morceaux.append(out)
    fond = work / "fond.mp4"
    if len(morceaux) == 1:
        morceaux[0].replace(fond)
        return fond
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for m in morceaux:
        cmd += ["-i", str(m)]
    filtres, prec = [], "[0:v]"
    for i in range(1, len(morceaux)):
        sortie = f"[x{i}]"
        filtres.append(f"{prec}[{i}:v]xfade=transition=fade:duration={FONDU}:offset={segments[i][0]:.3f}{sortie}")
        prec = sortie
    cmd += ["-filter_complex", ";".join(filtres), "-map", prec, "-c:v", "libx264", "-preset", "veryfast",
            "-crf", "18", "-pix_fmt", "yuv420p", str(fond)]
    subprocess.run(cmd, check=True)
    return fond


def fond_du_jour(mots: list[str], debuts_versets: list[float], total: float, interdits: set[str],
                 graine: str, work: Path) -> tuple[Path, list[dict]]:
    segments = plages(debuts_versets, total)
    clips = choisir(mots, len(segments), interdits, graine)
    fond = assembler(clips, segments, work)
    utilises = clips[:len(segments)]
    return fond, [{k: v for k, v in asdict(c).items() if k != "url"} for c in utilises]
