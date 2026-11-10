"""Chaîne complète d'une journée : choisir le passage, produire la vidéo, la vérifier."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from . import ecoute, layout, legende, sources, suivi, verification, video
from .decoupage import decouper


@dataclass
class Resultat:
    passage: suivi.Passage
    video: Path
    couverture: Path
    legende: str
    controles: list[str]


def charger_config() -> dict:
    cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    cfg["sourates"] = yaml.safe_load(Path("sourates.yaml").read_text(encoding="utf-8"))
    return cfg


def noms(cfg: dict) -> dict[int, str]:
    return {n: s["nom"] for n, s in cfg["sourates"]["sourates"].items()}


def _charger(cfg: dict, numero: int) -> sources.Surah:
    return sources.load_surah(numero, cfg["recitateur"]["id"], cfg["traduction"]["id"], noms(cfg))


def calculer_decoupage(cfg: dict, numero: int) -> list[list[int]]:
    surah = _charger(cfg, numero)
    sources.fetch_audio(surah.verses, cfg["recitateur"]["id"])
    durees, extra = [], 0.0
    for v in surah.verses:
        if v.number == 0:
            extra = v.duration
        else:
            durees.append(v.duration + extra)
            extra = 0.0
    return decouper(durees, cfg["decoupage"]["duree_min"], cfg["decoupage"]["duree_max"])


def produire(cfg: dict, passage: suivi.Passage, sortie: Path, fond: Path | None = None) -> Resultat:
    surah = _charger(cfg, passage.sourate)
    verses = [v for v in surah.verses
              if passage.debut <= v.number <= passage.fin or (v.number == 0 and passage.debut == 1)]
    sources.fetch_audio(verses, cfg["recitateur"]["id"])

    sortie.mkdir(parents=True, exist_ok=True)
    work = sortie / "calques"
    partie = (f"Partie {passage.partie}/{passage.total}" if passage.flux != "ramadan"
              else legende.versets(passage).capitalize())
    with layout.Renderer() as r:
        screens = video.build_screens(surah, verses, partie, work, r)
    audio = work / "audio.wav"
    audio_dur = video.concat_audio(verses, audio)
    out = sortie / "video.mp4"
    video.render(screens, audio, audio_dur, out, fond)

    controles = verification.controler(surah, passage, verses, screens, audio_dur,
                                       video.COVER + video.HOOK, video.END, out)
    if cfg["ecoute"]["active"]:
        problemes = ecoute.controler(verses, cfg["ecoute"]["seuil"])
        if problemes:
            raise verification.VerificationError(problemes)
        controles.append("audio reconnu conforme au texte de chaque verset")
    couverture = sortie / "couverture.png"
    shutil.copy(screens[0].png, couverture)
    texte = legende.legende(surah.name_latin, passage, cfg)
    (sortie / "legende.txt").write_text(texte + "\n", encoding="utf-8")
    return Resultat(passage, out, couverture, texte, controles)


def du_jour(cfg: dict, jour: date, state: dict) -> suivi.Passage | None:
    return suivi.prochain(state, jour, cfg, lambda n: calculer_decoupage(cfg, n))
