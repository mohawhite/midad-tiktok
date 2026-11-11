"""Contrôles avant publication. Au moindre échec, la vidéo est bloquée."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image

from . import layout
from .decoupage import VERSETS
from .layout import _letters
from .sources import Surah, Verse
from .suivi import Passage


class VerificationError(RuntimeError):
    def __init__(self, problemes: list[str]):
        super().__init__("Vérification échouée :\n- " + "\n- ".join(problemes))
        self.problemes = problemes


def controler(surah: Surah, passage: Passage, verses: list[Verse], screens: list, audio_dur: float,
              intro: float, fin: float, video: Path) -> list[str]:
    """Renvoie la liste des contrôles passés ; lève VerificationError sinon."""
    ko: list[str] = []
    ok: list[str] = []

    # Le texte lui-même est comparé à Quran.com au chargement (sources.load_surah).
    ok.append("texte arabe identique dans deux sources")

    if surah.verses_count != VERSETS[surah.number - 1]:
        ko.append(f"sourate {surah.number} : {surah.verses_count} versets au lieu de {VERSETS[surah.number - 1]}")
    nums = [v.number for v in verses if v.number > 0]
    if nums != list(range(passage.debut, passage.fin + 1)):
        ko.append(f"versets attendus {passage.debut}-{passage.fin}, obtenus {nums[:1]}…{nums[-1:]}")
    else:
        ok.append("nombre et numéros de versets conformes à la table de référence")

    for v in verses:
        stem = "basmala" if v.number == 0 else f"{v.surah:03d}{v.number:03d}"
        if v.audio_path is None or v.audio_path.stem != stem:
            ko.append(f"{v.key} : fichier audio inattendu")
        n = _letters(v.arabic)
        if not (0.05 * n <= v.duration <= 3 + 1.0 * n):
            ko.append(f"{v.key} : durée {v.duration:.1f} s peu plausible pour {n} lettres")
    ok.append("fichiers audio présents, bien numérotés, de durée plausible")

    texte = sum(s.end - s.start for s in screens[2:-1])
    if abs(texte - audio_dur) > 0.05:
        ko.append(f"écrans de texte : {texte:.3f} s pour {audio_dur:.3f} s d'audio")
    else:
        ok.append("durée des écrans égale à celle de l'audio")

    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
         "-of", "json", str(video)], check=True, capture_output=True, text=True).stdout)
    kinds = {s["codec_type"]: s for s in info["streams"]}
    attendu = intro + audio_dur + fin
    if "video" not in kinds or (kinds["video"]["width"], kinds["video"]["height"]) != (layout.W, layout.H):
        ko.append("la vidéo n'est pas en 1080 × 1920")
    if "audio" not in kinds:
        ko.append("la vidéo n'a pas de piste audio")
    if abs(float(info["format"]["duration"]) - attendu) > 0.2:
        ko.append(f"durée finale {info['format']['duration']} s, attendue {attendu:.2f} s")
    if not ko:
        ok.append("format 1080 × 1920, piste audio, durée conforme")

    # Tolérance de 8 px : l'encre d'une lettre arabe dépasse parfois légèrement de sa ligne.
    # Le logo du bas est volontairement placé sous la barre : seul le texte est contrôlé.
    tol = 8
    box = (layout.SAFE_SIDE - tol, layout.SAFE_TOP, layout.W - layout.SAFE_SIDE + tol, layout.BAR_Y - 10)
    for s in screens[1:-1]:
        b = Image.open(s.png).getchannel("A").crop((0, 0, layout.W, layout.BAR_Y)).getbbox()
        if b is None:
            ko.append(f"{s.label} : écran vide")
        elif b[0] < box[0] or b[1] < box[1] or b[2] > box[2] or b[3] > box[3]:
            ko.append(f"{s.label} : le texte déborde de la zone libre {b}")
    ok.append("aucun texte hors de la zone libre")

    if ko:
        raise VerificationError(ko)
    return ok
