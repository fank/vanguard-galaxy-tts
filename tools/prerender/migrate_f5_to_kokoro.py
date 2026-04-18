#!/usr/bin/env python3
"""Migrate English-Kokoro F5-cloned NPCs to Kokoro-direct.

56% of our F5 usage clones an English-language Kokoro voice — with no
accent benefit, since Kokoro already has that voice natively. Switching to
Kokoro-direct eliminates cloning fragments AND makes runtime live-TTS
produce byte-identical output (same ONNX model deterministically).

Non-English F5 references (Japanese/Hindi/Spanish/French/Portuguese) and
Piper Scottish stay on F5 — those are earning their cost via accent.

For each affected manifest entry, this script re-synthesizes with Kokoro
at the SID embedded in the reference name, overwrites the OGG, and updates
the manifest entry's engine/voice/params fields.
"""
from __future__ import annotations
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro
from score import score_wav
from paths import MANIFEST, ogg_path as _ogg_path, wav_path as _wav_path

# English-Kokoro F5 refs → their Kokoro SID (extracted from the ref name).
# Non-English refs (Japanese/Hindi/Spanish/French/Portuguese) and Piper
# Scottish are DELIBERATELY OMITTED — they keep F5 for accent value.
REFS_TO_SID: dict[str, int] = {
    "sid06_af_nicole": 6,
    "sid13_am_eric": 13,
    "sid14_am_fenrir": 14,
    "sid16_am_michael": 16,
    "sid17_am_onyx": 17,
    "sid18_am_puck": 18,
    "sid22_bf_isabella": 22,
    "sid23_bf_lily": 23,
    "sid24_bm_daniel": 24,
    "sid25_bm_fable": 25,
    "kokoro_af_jessica_4": 4,
    "kokoro_af_sky_10": 10,
    "kokoro_bf_emma_21": 21,
}


def write_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav: Path, ogg: Path, q: int = 4):
    ogg.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
         "-c:a", "libvorbis", "-q:a", str(q), str(ogg)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")


def main():
    manifest = json.loads(MANIFEST.read_text())
    todo = [(k, e) for k, e in manifest.items()
            if e.get("engine") == "f5" and e.get("reference") in REFS_TO_SID]
    print(f"Migrating {len(todo)} entries from F5 to Kokoro-direct\n")

    for i, (key, entry) in enumerate(todo, 1):
        text = entry.get("text_normalized") or entry.get("text_raw", "")
        speaker = entry.get("speaker", "_unknown")
        old_ref = entry["reference"]
        sid = REFS_TO_SID[old_ref]
        try:
            x, sr = kokoro.synth(text, str(sid))
        except Exception as e:
            print(f"  [{i:3d}/{len(todo)}] {speaker}: synth failed — {e}")
            continue
        s = score_wav(x, sr, text)
        wav_path = _wav_path(speaker, key)
        ogg_path = _ogg_path(speaker, key)
        write_wav(wav_path, x, sr)
        encode_ogg(wav_path, ogg_path)

        entry.update({
            "engine": "kokoro",
            "reference": f"kokoro:{sid}",
            "voice": f"kokoro:{sid}",
            "voice_name": f"kokoro_sid{sid}",
            "params": {"sid": sid, "speed": 1.0},
            "score_total": s.total,
            "source": "f5-to-kokoro-migration",
        })
        # Drop stale F5-era fields
        entry.pop("score", None)
        entry.pop("score_components", None)

        if i % 25 == 0 or i == len(todo):
            print(f"  [{i:3d}/{len(todo)}] {speaker:<25s} kokoro:{sid:<2d} s={s.total:.2f}")
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. {len(todo)} entries migrated. Manifest has {len(manifest)} total.")


if __name__ == "__main__":
    main()
