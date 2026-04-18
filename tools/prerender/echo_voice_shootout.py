#!/usr/bin/env python3
"""ECHO voice fatigue shootout.

ECHO plays ~173 HUD tips on heavy rotation, so its voice has to stay pleasant
on the 200th listen. The current pick is kokoro_bf_emma_21 (posh British F);
this renders the same 5 representative ECHO lines through each candidate so
we can pick by ear instead of by scoring metrics (which can't judge fatigue).

Outputs to prerender/echo_shootout/<ref>/<label>.wav.
"""
from __future__ import annotations
import sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import f5_engine as f5
import kokoro_engine as kokoro
from normalize import for_tts

REFDIR = Path(__file__).parent / "references"
OUT = Path(__file__).parent.parent.parent / "prerender" / "echo_shootout"

# 5 lines spanning ECHO's tonal range.
LINES = {
    "dreamy":      "Sometimes I just want to forget myself and fly into the sun. Its so pretty!",
    "excited":     "This music takes me places!",
    "teaching":    "Did you know that a hazard booster stops me from freaking out when in a hazard?",
    "playful":     "Sometimes I get stuck in a loop, I blame my programming.",
    "warm":        "You know, I think this partnership is going to work out just fine.",
}

# Candidate references. Each entry = (display name, kokoro SID if we need to
# generate the reference, pre-existing reference filename if any).
CANDIDATES = [
    # baseline — current ECHO voice, keep for A/B reference
    {"name": "kokoro_bf_emma_21",   "sid": 21, "existing": "kokoro_bf_emma_21"},
    # alternatives (all Kokoro v1.0)
    {"name": "kokoro_af_heart_3",   "sid": 3,  "existing": None},   # flagship warm F
    {"name": "kokoro_af_bella_2",   "sid": 2,  "existing": None},   # rich/mature F, A- grade
    {"name": "kokoro_af_nicole_6",  "sid": 6,  "existing": None},   # calm/whispery F
    {"name": "kokoro_bf_lily_23",   "sid": 23, "existing": None},   # softer British F than emma
    {"name": "kokoro_bf_isabella_22","sid": 22,"existing": "kokoro_bf_isabella_22"},  # gentler British F
]

REFERENCE_PHRASE = "Hello captain. This is ECHO speaking. Your ship is ready for launch."


def write_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def ensure_reference(name: str, sid: int) -> str:
    """Generate a Kokoro reference WAV + transcript if it doesn't already exist."""
    wav_path = REFDIR / f"{name}.wav"
    txt_path = REFDIR / f"{name}.txt"
    if wav_path.exists() and txt_path.exists():
        print(f"  {name}: reference exists, reusing")
        return name
    print(f"  {name}: generating Kokoro SID={sid} reference...")
    x, sr = kokoro.synth(REFERENCE_PHRASE, str(sid))
    write_wav(wav_path, x, sr)
    txt_path.write_text(REFERENCE_PHRASE)
    return name


def main():
    # Step 1: ensure all references exist
    print("=== Preparing references ===")
    refs = []
    for c in CANDIDATES:
        ref = ensure_reference(c["existing"] or c["name"], c["sid"])
        refs.append((c["name"], c["existing"] or c["name"]))

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Rendering {len(LINES)} lines × {len(refs)} voices = {len(LINES)*len(refs)} files ===\n")

    for label, text in LINES.items():
        norm = for_tts(text)
        for display_name, ref_name in refs:
            outpath = OUT / display_name / f"{label}.wav"
            if outpath.exists():
                print(f"  [{display_name}/{label}] exists, skipping")
                continue
            try:
                x, sr = f5.synth(norm, ref_name, seed=0)
                write_wav(outpath, x, sr)
                print(f"  [{display_name}/{label}] dur={len(x)/sr:.2f}s")
            except Exception as e:
                print(f"  [{display_name}/{label}] FAILED: {e}")

    print(f"\nDone. Audition files under: {OUT}")
    print("\nSuggested listening order (same line across voices):")
    for label in LINES:
        print(f"  --- {label!r} ---")
        for display_name, _ in refs:
            print(f"    {(OUT / display_name / f'{label}.wav').relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
