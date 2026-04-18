#!/usr/bin/env python3
"""ECHO voice fatigue shootout v2 — Kokoro direct (no F5 cloning).

v1 used F5-TTS voice cloning, which introduces fragment/hallucination artifacts.
User reported "fragments" on heart, emma, bella — that's an F5 signature, not a
base-voice issue. Kokoro v1.0 trained voices synthesize directly without cloning,
so they don't fragment.

Renders 5 ECHO lines through 8 Kokoro female voices directly, including the
ones v1 missed (af_sarah, af_aoede, af_alloy, af_kore, af_river, bf_alice).
"""
from __future__ import annotations
import sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro

OUT = Path(__file__).parent.parent.parent / "prerender" / "echo_shootout_kokoro"

LINES = {
    "dreamy":   "Sometimes I just want to forget myself and fly into the sun. Its so pretty!",
    "excited":  "This music takes me places!",
    "teaching": "Did you know that a hazard booster stops me from freaking out when in a hazard?",
    "playful":  "Sometimes I get stuck in a loop, I blame my programming.",
    "warm":     "You know, I think this partnership is going to work out just fine.",
}

# All English female Kokoro voices, tested and untested.
# Grouped so listening can start with untested ones (user already heard F5 variants).
VOICES = [
    # Previously heard via F5 — include for Kokoro-direct A/B
    (21, "bf_emma",     "current ECHO — F5 had fragments, direct should be clean"),
    (22, "bf_isabella", "F5 sounded nice but high, direct may settle"),
    # Untested — fresh options
    ( 9, "af_sarah",    "American F, softer than af_bella"),
    ( 1, "af_aoede",    "American F, mellow mid-register"),
    ( 0, "af_alloy",    "American F, even tone"),
    ( 5, "af_kore",     "American F, warm"),
    ( 8, "af_river",    "American F, airy"),
    (20, "bf_alice",    "British F, untested"),
]


def write_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"=== Rendering {len(LINES)} lines × {len(VOICES)} Kokoro voices = {len(LINES)*len(VOICES)} files ===\n")
    for sid, name, note in VOICES:
        print(f"[SID {sid:2d}] {name} — {note}")
        for label, text in LINES.items():
            outpath = OUT / f"{sid:02d}_{name}" / f"{label}.wav"
            if outpath.exists():
                print(f"    {label}: exists, skip")
                continue
            try:
                x, sr = kokoro.synth(text, str(sid))
                write_wav(outpath, x, sr)
                print(f"    {label}: dur={len(x)/sr:.2f}s peak={np.abs(x).max():.2f}")
            except Exception as e:
                print(f"    {label}: FAILED: {e}")

    print(f"\nDone. Listen under: {OUT}")
    print("\nSuggested: play the SAME line across all voices back-to-back:")
    for label in LINES:
        print(f"  --- {label!r} ---")
        for sid, name, _ in VOICES:
            rel = (OUT / f"{sid:02d}_{name}" / f"{label}.wav").relative_to(OUT.parent.parent)
            print(f"    {rel}")


if __name__ == "__main__":
    main()
