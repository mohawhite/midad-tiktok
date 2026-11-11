"""Ligne de commande de Midad."""
from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from . import pipeline, publication, suivi
from .decoupage import VERSETS


def _essai(args, cfg) -> None:
    fin_sourate = VERSETS[args.sourate - 1]
    a, b = (int(x) for x in args.versets.split("-")) if args.versets else (1, fin_sourate)
    p = suivi.Passage("principal", args.sourate, a, b, args.partie, args.total)
    _afficher(pipeline.produire(cfg, p, args.sortie / f"essai_{args.sourate:03d}_{a}-{b}", args.fond))


def _jour(args, cfg) -> None:
    jour = date.fromisoformat(args.date) if args.date else date.today()
    state = suivi.charger()
    passage = pipeline.du_jour(cfg, jour, state)
    if passage is None:
        print(f"Rien à faire pour le {jour.isoformat()} : la vidéo du jour existe déjà.")
        return
    res = pipeline.produire(cfg, passage, args.sortie / jour.isoformat(), args.fond,
                            suivi.clips_de_la_veille(state))
    _afficher(res)
    if args.dry_run:
        print("Mode essai : rien n'est publié, le suivi n'est pas modifié.")
        return
    mode, identifiant = publication.publier(res, cfg, jour)
    suivi.enregistrer(state, passage, jour, mode, identifiant, res.clips)
    suivi.sauver(state)
    print(f"Suivi mis à jour ({mode}).")
    sortie = os.environ.get("GITHUB_OUTPUT")
    if sortie:
        with open(sortie, "a", encoding="utf-8") as f:
            f.write(f"mode={mode}\n")


def _afficher(res: pipeline.Resultat) -> None:
    print(f"Vidéo : {res.video}")
    print("Contrôles passés :")
    for c in res.controles:
        print(f"  - {c}")
    for c in res.clips:
        print(f"Clip : {c['id']} ({c['auteur']}) {c['lien']}")
    print("Légende :\n" + res.legende)


def main() -> None:
    p = argparse.ArgumentParser(prog="midad")
    p.add_argument("--sortie", type=Path, default=Path("out"))
    p.add_argument("--fond", type=Path, help="clip vidéo de fond (sinon fond provisoire uni)")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("essai", help="produit un passage choisi, sans publier")
    e.add_argument("--sourate", type=int, required=True)
    e.add_argument("--versets", help="plage, par exemple 1-7 (par défaut : toute la sourate)")
    e.add_argument("--partie", type=int, default=1)
    e.add_argument("--total", type=int, default=1)
    j = sub.add_parser("jour", help="produit la vidéo prévue pour une date")
    j.add_argument("--date", help="AAAA-MM-JJ (par défaut : aujourd'hui)")
    j.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    cfg = pipeline.charger_config()
    {"essai": _essai, "jour": _jour}[args.cmd](args, cfg)


if __name__ == "__main__":
    main()
