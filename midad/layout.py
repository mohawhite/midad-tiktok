"""Mise en page : rendu des calques de texte en PNG avec Chromium, et découpage des versets longs."""
from __future__ import annotations

import html
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import sync_playwright

FONTS = Path(__file__).resolve().parent.parent / "fonts"
W, H = 1080, 1920
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 160, 480, 140
MAX_ARABIC_LINES = 3
PAUSE_MARKS = set("ۖۗۘۙۚۛۜ")

CSS = f"""
@font-face {{ font-family: 'Aref Ruqaa'; font-weight: 700; src: url('{(FONTS / "ArefRuqaa-Bold.ttf").as_uri()}'); }}
@font-face {{ font-family: 'Amiri Quran'; src: url('{(FONTS / "AmiriQuran-Regular.ttf").as_uri()}'); }}
@font-face {{ font-family: 'Inter'; font-weight: 100 900; src: url('{(FONTS / "Inter.ttf").as_uri()}'); }}
html, body {{ margin: 0; background: transparent; }}
.frame {{ position: relative; width: {W}px; height: {H}px; overflow: hidden; color: #fff;
  font-family: 'Inter', sans-serif; text-align: center; }}
.safe {{ position: absolute; inset: 0; box-sizing: border-box;
  padding: {SAFE_TOP}px {SAFE_SIDE}px {SAFE_BOTTOM}px; display: flex; flex-direction: column; align-items: center; }}
.center {{ justify-content: center; }}
.ruqaa {{ font-family: 'Aref Ruqaa', serif; font-weight: 700; direction: rtl; }}
.caps {{ font-weight: 500; text-transform: uppercase; }}
.rule {{ background: #fff; }}
.ref {{ font-size: 32px; font-weight: 500; letter-spacing: 0.12em; padding-top: 24px; text-transform: uppercase; }}
.body {{ flex-grow: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 56px;
  padding-bottom: 80px; }}
.ar {{ font-family: 'Amiri Quran', serif; font-size: 84px; line-height: 2; direction: rtl; }}
.fr {{ font-size: 46px; font-weight: 400; line-height: 1.4; }}
"""


def _page(inner: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{inner}</body></html>"


def _e(text: str) -> str:
    return html.escape(text)


def _spaced(text: str, size: int, spacing: float, weight: int = 500) -> str:
    return (f"<div class='caps' style='font-size:{size}px;font-weight:{weight};"
            f"letter-spacing:{spacing}em;margin-right:-{spacing}em'>{_e(text)}</div>")


def _logo(mot: int) -> str:
    """Le logo Midad, avec exactement les proportions de la photo de profil
    (mot de 300 px, espace de 28 px, trait de 56 × 2 px, « MIDAD » en 34 px)."""
    e = mot / 300
    return (f"<div style='display:flex;flex-direction:column;align-items:center;gap:{28 * e:.1f}px'>"
            f"<div class='ruqaa' style='font-size:{mot}px;line-height:1.1'>مداد</div>"
            f"<div class='rule' style='width:{56 * e:.1f}px;height:{max(1.0, 2 * e):.1f}px'></div>"
            f"<div style='font-size:{34 * e:.1f}px;font-weight:500;letter-spacing:0.5em;margin-right:-0.5em'>MIDAD</div>"
            "</div>")


# Logo du bas : même taille et même place sur la miniature, l'accroche et chaque verset.
LOGO_BAS = 340  # distance entre le bas du logo et le bas de l'écran
PIED = (f"<div id='pied' style='position:absolute;left:0;right:0;bottom:{LOGO_BAS}px;display:flex;"
        f"justify-content:center'>{_logo(110)}</div>")
BAR_Y = H - SAFE_BOTTOM - 44  # position de la barre de progression


def cover_html(number: int, name_ar: str, name_lat: str, part: str) -> str:
    return _page(
        "<div class='frame' style='background:#000'>"
        "<div style='position:absolute;top:240px;left:0;width:1080px;height:1440px;box-sizing:border-box;"
        "padding:120px 120px 100px;display:flex;flex-direction:column;align-items:center;justify-content:space-between'>"
        f"{_spaced(f'Sourate {number}', 40, 0.3)}"
        "<div style='display:flex;flex-direction:column;align-items:center;gap:44px'>"
        f"<div class='ruqaa' style='font-size:250px;line-height:1.2'>{_e(name_ar)}</div>"
        "<div class='rule' style='width:72px;height:3px'></div>"
        f"{_spaced(name_lat, 60, 0.4)}"
        f"<div style='font-size:48px'>{_e(part)}</div></div>"
        f"<div></div></div>{PIED}</div>"
    )


def hook_html(name_ar: str, name_lat: str, verses: str) -> str:
    return _page(
        "<div class='frame'><div class='safe'>"
        "<div class='body' style='gap:44px'>"
        f"<div class='ruqaa' style='font-size:230px;line-height:1.2'>{_e(name_ar)}</div>"
        "<div class='rule' style='width:72px;height:3px'></div>"
        f"{_spaced(name_lat, 54, 0.4)}"
        f"<div style='font-size:44px'>{_e(verses)}</div></div></div>{PIED}</div>"
    )


def end_html() -> str:
    """Fin : le logo seul, au centre, sur fond noir."""
    return _page(
        "<div class='frame' style='background:#000'><div style='position:absolute;inset:0;display:flex;"
        f"align-items:center;justify-content:center'>{_logo(320)}</div></div>"
    )


def verse_html(ref: str, arabic: str, french: str) -> str:
    return _page(
        "<div class='frame'><div class='safe'>"
        f"<div class='ref'>{_e(ref)}</div>"
        f"<div class='body'><div class='ar' id='ar'>{_e(arabic)}</div>"
        f"<div class='fr' id='fr'>{_e(french)}</div></div></div>{PIED}</div>"
    )


@dataclass
class Chunk:
    arabic: str
    french: str
    weight: float  # part de la durée du verset


def _letters(text: str) -> int:
    return sum(1 for ch in text if unicodedata.category(ch).startswith("L"))


def _tokens(arabic: str) -> list[str]:
    """Mots, chaque marque de pause isolée restant collée au mot qui la précède."""
    out: list[str] = []
    for tok in arabic.split(" "):
        if out and tok and all(ch in PAUSE_MARKS or unicodedata.category(ch) == "Mn" for ch in tok):
            out[-1] += " " + tok
        elif tok:
            out.append(tok)
    return out


def _split_arabic(arabic: str, k: int) -> list[str]:
    toks = _tokens(arabic)
    if k <= 1 or len(toks) < 2:
        return [arabic]
    k = min(k, len(toks))
    sizes = [_letters(t) for t in toks]
    total = sum(sizes) or 1
    cum, acc = [], 0
    for s in sizes:
        acc += s
        cum.append(acc)
    cuts: list[int] = []
    for i in range(1, k):
        target = total * i / k
        lo = (cuts[-1] + 1) if cuts else 0
        cands = list(range(lo, len(toks) - (k - i)))
        if not cands:
            break
        window = total / k * 0.3
        pauses = [j for j in cands if any(ch in PAUSE_MARKS for ch in toks[j]) and abs(cum[j] - target) <= window]
        pool = pauses or cands
        cuts.append(min(pool, key=lambda j: abs(cum[j] - target)))
    parts, start = [], 0
    for c in cuts:
        parts.append(" ".join(toks[start:c + 1]))
        start = c + 1
    parts.append(" ".join(toks[start:]))
    return parts


def _split_french(french: str, shares: list[float]) -> list[str]:
    words = french.split(" ")
    if len(shares) == 1 or len(words) < len(shares):
        return [french] + [""] * (len(shares) - 1)
    total = sum(len(w) + 1 for w in words)
    cum, acc = [], 0
    for w in words:
        acc += len(w) + 1
        cum.append(acc)
    cuts, done = [], 0.0
    for i, share in enumerate(shares[:-1]):
        done += share
        target = total * done
        lo = (cuts[-1] + 1) if cuts else 0
        cands = list(range(lo, len(words) - (len(shares) - 1 - i)))
        window = total / len(shares) * 0.3
        punct = [j for j in cands if words[j][-1:] in ",;:.!?»" and abs(cum[j] - target) <= window]
        pool = punct or cands
        cuts.append(min(pool, key=lambda j: abs(cum[j] - target)))
    parts, start = [], 0
    for c in cuts:
        parts.append(" ".join(words[start:c + 1]))
        start = c + 1
    parts.append(" ".join(words[start:]))
    return parts


class Renderer:
    """Un navigateur Chromium sans interface, ouvert le temps d'une vidéo."""

    def __enter__(self) -> "Renderer":
        self._pw = sync_playwright().start()
        exe = os.environ.get("MIDAD_CHROMIUM")
        self._browser = self._pw.chromium.launch(executable_path=exe) if exe else self._pw.chromium.launch()
        self._page = self._browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        self._dir = tempfile.TemporaryDirectory()
        self._tmp = Path(self._dir.name) / "page.html"
        return self

    def __exit__(self, *exc) -> None:
        self._browser.close()
        self._pw.stop()
        self._dir.cleanup()

    def _load(self, page_html: str) -> None:
        # Chromium refuse les polices locales depuis une page sans adresse : on passe par un fichier.
        self._tmp.write_text(page_html, encoding="utf-8")
        self._page.goto(self._tmp.as_uri())
        loaded = self._page.evaluate(
            """async () => {
              const fonts = ['700 20px "Aref Ruqaa"', '20px "Amiri Quran"', '400 20px Inter', '500 20px Inter'];
              const res = await Promise.all(fonts.map(f => document.fonts.load(f, 'مداد Aa')));
              await document.fonts.ready;
              return res.map(r => r.length);
            }"""
        )
        if not all(loaded):
            raise RuntimeError(f"Polices non chargées : {loaded}")

    def png(self, page_html: str, out: Path, *, opaque: bool = False) -> Path:
        self._load(page_html)
        self._page.screenshot(path=str(out), omit_background=not opaque)
        return out

    def _fits(self, arabic: str, french: str) -> bool:
        self._load(verse_html("X · 1:1", arabic, french))
        m = self._page.evaluate(
            """() => {
              const ar = document.getElementById('ar'), fr = document.getElementById('fr');
              const body = ar.parentElement, ref = document.querySelector('.ref');
              const lh = parseFloat(getComputedStyle(ar).lineHeight);
              return {lines: Math.round(ar.getBoundingClientRect().height / lh),
                      overflowX: Math.max(ar.scrollWidth, fr.scrollWidth) > body.clientWidth + 1,
                      top: ar.getBoundingClientRect().top, refBottom: ref.getBoundingClientRect().bottom,
                      bottom: fr.getBoundingClientRect().bottom};
            }"""
        )
        # Le texte doit rester sous le repère du haut et au-dessus de la barre de progression.
        return (m["lines"] <= MAX_ARABIC_LINES and not m["overflowX"]
                and m["top"] >= m["refBottom"] + 20 and m["bottom"] <= BAR_Y - 30)

    def split_verse(self, arabic: str, french: str) -> list[Chunk]:
        """Découpe un verset en autant d'écrans que nécessaire, sans jamais réduire le texte."""
        for k in range(1, 40):
            ar_parts = _split_arabic(arabic, k)
            if len(ar_parts) < k:
                break
            sizes = [_letters(p) or 1 for p in ar_parts]
            shares = [s / sum(sizes) for s in sizes]
            fr_parts = _split_french(french, shares)
            if all(self._fits(a, f) for a, f in zip(ar_parts, fr_parts)):
                return [Chunk(a, f, s) for a, f, s in zip(ar_parts, fr_parts, shares)]
        raise RuntimeError("Impossible de faire tenir ce verset à l'écran")
