"""Planning et fichier de suivi : quel passage publier aujourd'hui, sans répétition ni saut."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from hijridate import Gregorian

FICHIER = Path("suivi.json")
Decoupeur = Callable[[int], list[list[int]]]


@dataclass
class Passage:
    flux: str          # principal, vendredi ou ramadan
    sourate: int
    debut: int
    fin: int
    partie: int        # à partir de 1
    total: int


def vide() -> dict:
    return {
        "version": 1,
        "decoupages": {},
        "positions": {"principal": {"index": 0, "partie": 0}, "vendredi": 0,
                      "ramadan": {"annee": 0, "index": 0}},
        "publications": [],
    }


def charger(path: Path = FICHIER) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else vide()


def sauver(state: dict, path: Path = FICHIER) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def ordre(cfg: dict) -> list[int]:
    out: list[int] = []
    for bloc in cfg["ordre"]:
        out += list(range(bloc["de"], bloc["a"] + 1)) if isinstance(bloc, dict) else list(bloc)
    if sorted(out) != list(range(1, 115)):
        raise ValueError("config.yaml : l'ordre doit contenir chaque sourate exactement une fois")
    return out


def hegire(jour: date) -> tuple[int, int]:
    h = Gregorian(jour.year, jour.month, jour.day).to_hijri()
    return h.year, h.month


def decoupage(state: dict, sourate: int, calculer: Decoupeur) -> list[list[int]]:
    """Le découpage est calculé une seule fois, puis figé dans le suivi."""
    key = str(sourate)
    if key not in state["decoupages"]:
        state["decoupages"][key] = calculer(sourate)
    return state["decoupages"][key]


def prochain(state: dict, jour: date, cfg: dict, calculer: Decoupeur) -> Passage | None:
    """Passage du jour, ou None si ce jour a déjà sa vidéo ou si tout est publié."""
    if any(p["date"] == jour.isoformat() for p in state["publications"]):
        return None
    pos = state["positions"]
    if jour.weekday() == 4 and cfg.get("vendredi"):
        s = cfg["vendredi"]["sourate"]
        parts = decoupage(state, s, calculer)
        i = pos["vendredi"] % len(parts)
        return Passage("vendredi", s, parts[i][0], parts[i][1], i + 1, len(parts))
    annee, mois = hegire(jour)
    liste = cfg.get("ramadan") or []
    if mois == 9 and liste:
        i = pos["ramadan"]["index"] if pos["ramadan"]["annee"] == annee else 0
        if i < len(liste):
            r = liste[i]
            return Passage("ramadan", r["sourate"], r["versets"][0], r["versets"][1], 1, 1)
    seq = ordre(cfg)
    if pos["principal"]["index"] >= len(seq):
        return None
    s = seq[pos["principal"]["index"]]
    parts = decoupage(state, s, calculer)
    i = pos["principal"]["partie"]
    return Passage("principal", s, parts[i][0], parts[i][1], i + 1, len(parts))


def enregistrer(state: dict, passage: Passage, jour: date, mode: str, identifiant: str = "",
                clips: list | None = None) -> None:
    """À appeler uniquement après une publication réussie ou une remise en plan B."""
    if any(p["date"] == jour.isoformat() for p in state["publications"]):
        raise ValueError(f"Une vidéo est déjà enregistrée pour le {jour.isoformat()}")
    pos = state["positions"]
    if passage.flux == "vendredi":
        pos["vendredi"] = passage.partie % passage.total
    elif passage.flux == "ramadan":
        annee, _ = hegire(jour)
        i = pos["ramadan"]["index"] if pos["ramadan"]["annee"] == annee else 0
        pos["ramadan"] = {"annee": annee, "index": i + 1}
    elif passage.partie >= passage.total:
        pos["principal"] = {"index": pos["principal"]["index"] + 1, "partie": 0}
    else:
        pos["principal"]["partie"] = passage.partie
    state["publications"].append(
        {"date": jour.isoformat(), **asdict(passage), "mode": mode, "id": identifiant, "clips": clips or []}
    )


def clips_de_la_veille(state: dict) -> set[str]:
    if not state["publications"]:
        return set()
    return {c["id"] for c in state["publications"][-1].get("clips", [])}
