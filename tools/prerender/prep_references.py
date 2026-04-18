#!/usr/bin/env python3
"""Generate F5-TTS reference WAVs from Kokoro speakers.

F5-TTS quality is driven by the reference voice. The default F5 reference is a
generic American female; for ECHO we want a British AI feel. Kokoro v1.0 has
several British female speakers. We synthesize a short reference sentence with
each, saving WAV + transcript pairs F5 can then clone.
"""
from __future__ import annotations
import sys, wave, numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro  # noqa: E402

OUTDIR = Path(__file__).parent / "references"

# Reference phrase choices — picked for phonemic variety (vowels, consonants,
# questions) so F5 has enough signal to characterize the voice.
REFS = [
    ("kokoro_bf_emma_21", "21",
     "Hello captain. This is ECHO speaking. Your ship is ready for launch."),
    ("kokoro_bf_isabella_22", "22",
     "Hello captain. This is ECHO speaking. Your ship is ready for launch."),
    ("kokoro_af_nova_7", "7",
     "Hello captain. This is ECHO speaking. Your ship is ready for launch."),
    ("kokoro_af_jessica_4", "4",
     "Hello captain. This is ECHO speaking. Your ship is ready for launch."),
    ("kokoro_af_sky_10", "10",
     "Hello captain. This is ECHO speaking. Your ship is ready for launch."),
]


def save_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for name, voice, transcript in REFS:
        print(f"Generating {name} (Kokoro SID {voice})...")
        x, sr = kokoro.synth(transcript, voice)
        save_wav(OUTDIR / f"{name}.wav", x, sr)
        (OUTDIR / f"{name}.txt").write_text(transcript)
    print(f"\nWrote {len(REFS)} reference pairs to {OUTDIR}")


if __name__ == "__main__":
    main()
