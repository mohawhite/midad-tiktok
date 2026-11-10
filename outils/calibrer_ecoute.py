"""Calibre le seuil du contrôle par reconnaissance vocale sur des versets réels.

Usage : python -m outils.calibrer_ecoute
Pour chaque verset, compare la transcription au bon texte (« bon ») et aux autres
versets du même lot (« mauvais ») : le seuil doit se situer entre les deux.
"""
import time

from midad import ecoute, pipeline, sources

LOTS = [(1, 1, 7), (112, 1, 4), (2, 1, 20), (2, 282, 282), (18, 1, 10), (36, 1, 12)]


def main() -> None:
    cfg = pipeline.charger_config()
    rows = []
    for n, a, b in LOTS:
        surah = pipeline._charger(cfg, n)
        vs = [v for v in surah.verses if a <= v.number <= b or (v.number == 0 and a == 1)]
        sources.fetch_audio(vs, cfg["recitateur"]["id"])
        for i, v in enumerate(vs):
            t = time.time()
            entendu = ecoute.transcrire(v.audio_path)
            dt = time.time() - t
            bon = ecoute.ressemblance(entendu, v.arabic)
            mauvais = max((ecoute.ressemblance(entendu, w.arabic) for j, w in enumerate(vs) if j != i), default=0)
            rows.append((bon, mauvais, v.key, round(v.duration, 1), round(dt, 1)))
    rows.sort()
    for r in rows[:12]:
        print(f"bon {r[0]:.3f}  mauvais {r[1]:.3f}  {r[2]}  audio {r[3]} s  calcul {r[4]} s")
    print(f"{len(rows)} versets ; plus faible « bon » : {rows[0][0]:.3f} ; "
          f"plus fort « mauvais » : {max(r[1] for r in rows):.3f}")
    print(f"calcul : {sum(r[4] for r in rows):.0f} s pour {sum(r[3] for r in rows):.0f} s d'audio")


if __name__ == "__main__":
    main()
