"""Montage : assemble l'audio, le fond et les calques de texte avec FFmpeg."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import layout
from .sources import Surah, Verse

FPS = 30
COVER = 0.7   # miniature, sert de couverture (image 0)
HOOK = 1.8    # accroche
END = 2.5     # logo de fin, sur fond noir
FADE = 0.25   # fondu des écrans de versets
FADE_INTRO = 0.4
FADE_FIN = 0.6
BAR_W, BAR_H = 800, 4
BAR_Y = layout.H - layout.SAFE_BOTTOM - 44


@dataclass
class Screen:
    png: Path
    start: float
    end: float
    label: str
    opaque: bool = False
    fade_in: float = FADE
    fade_out: float = FADE


def verse_range_label(verses: list[Verse]) -> str:
    nums = [v.number for v in verses if v.number > 0]
    return f"Verset {nums[0]}" if len(nums) == 1 else f"Versets {nums[0]} à {nums[-1]}"


def build_screens(surah: Surah, verses: list[Verse], part: str, work: Path, r: layout.Renderer) -> list[Screen]:
    work.mkdir(parents=True, exist_ok=True)
    screens = [
        Screen(r.png(layout.cover_html(surah.number, surah.name_arabic, surah.name_latin, part),
                     work / "cover.png", opaque=True), 0.0, COVER, "miniature", opaque=True,
               fade_in=0, fade_out=FADE_INTRO),
        Screen(r.png(layout.hook_html(surah.name_arabic, surah.name_latin, verse_range_label(verses)),
                     work / "hook.png"), COVER, COVER + HOOK, "accroche", fade_in=FADE_INTRO, fade_out=FADE_INTRO),
    ]
    t = COVER + HOOK
    for v in verses:
        ref = surah.name_latin if v.number == 0 else f"{surah.name_latin} · {v.key}"
        chunks = r.split_verse(v.arabic, v.french)
        for i, c in enumerate(chunks):
            d = v.duration * c.weight
            png = r.png(layout.verse_html(ref, c.arabic, c.french), work / f"v{v.number:03d}_{i}.png")
            screens.append(Screen(png, t, t + d, f"{v.key} écran {i + 1}/{len(chunks)}"))
            t += d
    screens[-1].fade_out = FADE_FIN  # le dernier verset s'efface doucement avant le logo
    screens.append(Screen(r.png(layout.end_html(), work / "end.png", opaque=True), t, t + END, "fin",
                          opaque=True, fade_in=FADE_FIN, fade_out=0))
    return screens


def concat_audio(verses: list[Verse], out: Path) -> float:
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{v.audio_path.resolve()}'\n" for v in verses), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True)
    return sum(v.duration for v in verses)


def render(screens: list[Screen], audio: Path, audio_dur: float, out: Path, background: Path | None = None) -> None:
    total = screens[-1].end
    intro = COVER + HOOK
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if background:
        cmd += ["-stream_loop", "-1", "-i", str(background)]
    else:  # fond provisoire, tant qu'aucun clip n'est fourni
        cmd += ["-f", "lavfi", "-i", f"color=c=0x2a2f38:s={layout.W}x{layout.H}:r={FPS}"]
    cmd += ["-i", str(audio)]
    for s in screens:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{s.end - s.start:.4f}", "-i", str(s.png)]

    f = [
        f"color=c=black:s={layout.W}x{layout.H}:r={FPS}:d={total:.4f}[black]",
        f"[0:v]scale={layout.W}:{layout.H}:force_original_aspect_ratio=increase,crop={layout.W}:{layout.H},"
        f"fps={FPS},format=rgba,colorchannelmixer=aa=0.5[bg]",
        "[black][bg]overlay=shortest=1[base]",
        # barre de progression : une bande blanche glisse dans une fenêtre de 800 px
        f"color=c=white@0.3:s={BAR_W}x{BAR_H}:r={FPS}:d={total:.4f},format=rgba[track]",
        f"color=c=white:s={BAR_W}x{BAR_H}:r={FPS}:d={total:.4f},format=rgba[fill]",
        f"[track][fill]overlay=x='-{BAR_W}+{BAR_W}*min(max((t-{intro})/{audio_dur:.4f},0),1)':y=0[bar]",
        f"[base][bar]overlay=x={layout.SAFE_SIDE}:y={BAR_Y}:enable='between(t,{intro},{intro + audio_dur:.4f})'[withbar]",
    ]
    labels = []
    for i, s in enumerate(screens):
        d = s.end - s.start
        fin, fout = min(s.fade_in, d / 3), min(s.fade_out, d / 3)
        chain = f"[{i + 2}:v]format=rgba,fps={FPS}"
        if fin > 0:
            chain += f",fade=t=in:st=0:d={fin:.3f}:alpha=1"
        if fout > 0:
            chain += f",fade=t=out:st={d - fout:.4f}:d={fout:.3f}:alpha=1"
        f.append(chain + f"[s{i}]")
        labels.append(f"[s{i}]")
    f.append("".join(labels) + f"concat=n={len(screens)}:v=1:a=0[text]")
    f.append("[withbar][text]overlay=eof_action=pass[v]")
    f.append(f"[1:a]afade=t=in:d=0.1,afade=t=out:st={audio_dur - 0.3:.4f}:d=0.3,"
             f"adelay={int(intro * 1000)}:all=1,apad=whole_dur={total:.4f}[a]")

    cmd += ["-filter_complex", ";".join(f), "-map", "[v]", "-map", "[a]", "-t", f"{total:.4f}",
            "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
