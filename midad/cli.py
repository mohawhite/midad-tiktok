"""Ligne de commande. Pour l'instant : produire une vidéo d'essai, sans rien publier."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from . import layout, sources, video


def main() -> None:
    p = argparse.ArgumentParser(prog="midad")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("essai", help="produit une vidéo sans la publier")
    s.add_argument("--sourate", type=int, required=True)
    s.add_argument("--versets", help="plage, par exemple 1-7 (par défaut : toute la sourate)")
    s.add_argument("--partie", default="Partie 1/1")
    s.add_argument("--fond", type=Path, help="clip vidéo de fond (sinon fond provisoire uni)")
    s.add_argument("--sortie", type=Path, default=Path("out"))
    args = p.parse_args()

    cfg = yaml.safe_load(Path("config.yaml").read_text(encoding="utf-8"))
    surah = sources.load_surah(args.sourate, cfg["recitateur"]["id"], cfg["traduction"]["id"],
                               cfg.get("noms_sourates"))
    verses = surah.verses
    if args.versets:
        a, b = (int(x) for x in args.versets.split("-"))
        verses = [v for v in verses if a <= v.number <= b or (v.number == 0 and a == 1)]
    sources.fetch_audio(verses, cfg["recitateur"]["id"])

    args.sortie.mkdir(parents=True, exist_ok=True)
    stem = f"sourate{surah.number:03d}"
    work = args.sortie / f"{stem}_calques"
    with layout.Renderer() as r:
        screens = video.build_screens(surah, verses, args.partie, work, r)
    audio = work / "audio.wav"
    audio_dur = video.concat_audio(verses, audio)
    out = args.sortie / f"{stem}.mp4"
    video.render(screens, audio, audio_dur, out, args.fond)
    for sc in screens:
        print(f"{sc.start:7.2f} → {sc.end:7.2f}  {sc.label}")
    print(f"Vidéo : {out} ({screens[-1].end:.1f} s)")


if __name__ == "__main__":
    main()
