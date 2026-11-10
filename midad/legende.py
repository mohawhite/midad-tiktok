"""Légende TikTok générée pour chaque vidéo."""
from __future__ import annotations

import re
import unicodedata

from .suivi import Passage


def hashtag(nom: str) -> str:
    ascii_ = unicodedata.normalize("NFD", nom).encode("ascii", "ignore").decode()
    return "#" + re.sub(r"[^a-z0-9]", "", ascii_.lower())


def versets(p: Passage) -> str:
    return f"verset {p.debut}" if p.debut == p.fin else f"versets {p.debut} à {p.fin}"


def titre(nom: str, p: Passage) -> str:
    if p.total > 1:
        return f"{nom}, partie {p.partie}/{p.total} ({versets(p)})"
    return f"{nom} ({versets(p)})"


def legende(nom: str, p: Passage, cfg: dict) -> str:
    tags = list(cfg["legende"]["hashtags"])[:4]
    tag = hashtag(nom)
    if tag not in tags:
        tags.append(tag)
    texte = "\n".join([
        titre(nom, p),
        f"Récitation : {cfg['recitateur']['nom']}",
        f"Traduction : {cfg['traduction']['nom']}",
        "Texte : Tanzil.net",
        " ".join(tags),
    ])
    if len(texte) > cfg["legende"]["longueur_max"]:
        raise ValueError("Légende trop longue pour TikTok")
    return texte
