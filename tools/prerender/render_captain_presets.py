#!/usr/bin/env python3
"""Render all 281 captain lines through 6 voice presets (3 male, 3 female).

Players choose their captain's voice via [Voice] CaptainPreset in the config
(default picks m1 or f1 based on commander gender). Each preset lands in its
own prerender/<speaker>/ folder with manifest entries keyed by (text, preset_speaker).

Keys must recompute from the new speaker names — captain_m1 ≠ captain_m2 ≠ captain.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro
from score import score_wav
from paths import PACK, MANIFEST, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel

# Captain voice presets: (preset_name, kokoro_sid, friendly_label)
PRESETS = [
    ("captain_m1", 14, "am_fenrir (rugged American explorer)"),
    ("captain_m2", 17, "am_onyx (deep, confident)"),
    ("captain_m3", 25, "bm_fable (British rogue)"),
    ("captain_f1",  0, "af_alloy (calm teacher)"),
    ("captain_f2", 20, "bf_alice (British)"),
    ("captain_f3",  3, "af_heart (warm flagship)"),
]

CORPUS = Path("/tmp/captain_lines.json")


def compute_key(text: str, speaker: str) -> str:
    """Must match C# PrerenderLookup.ComputeKey exactly."""
    buf = text.encode("utf-8") + b"\x00" + speaker.encode("utf-8")
    return hashlib.sha256(buf).hexdigest()


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
    lines = json.loads(CORPUS.read_text())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    print(f"Captain corpus: {len(lines)} lines")
    print(f"Presets: {len(PRESETS)}")
    print(f"Total renders: {len(lines) * len(PRESETS)}\n")

    total = 0
    for preset_name, sid, label in PRESETS:
        print(f"=== {preset_name}  (Kokoro SID {sid}, {label}) ===")
        for i, line in enumerate(lines, 1):
            text = line["text_normalized"]
            if not text:
                continue
            key = compute_key(text, preset_name)
            if key in manifest:
                continue  # already rendered
            try:
                x, sr = kokoro.synth(text, str(sid))
            except Exception as e:
                print(f"  [{i}/{len(lines)}] synth failed: {e}")
                continue
            s = score_wav(x, sr, text)
            wav_path = _wav_path(preset_name, key)
            ogg_path = _ogg_path(preset_name, key)
            write_wav(wav_path, x, sr)
            encode_ogg(wav_path, ogg_path)
            manifest[key] = {
                "key": key,
                "speaker": preset_name,
                "text_normalized": text,
                "text_raw": line.get("text_raw", text),
                "engine": "kokoro",
                "voice": f"kokoro:{sid}",
                "voice_name": label,
                "params": {"sid": sid, "speed": 1.0},
                "score_total": s.total,
                "ogg": manifest_ogg_rel(preset_name, key),
                "source": "captain-preset-render",
            }
            total += 1
            if i % 25 == 0:
                print(f"  [{i:3d}/{len(lines)}] {text[:60]!r}  s={s.total:.2f}")
                MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print()

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Done. Rendered {total} new entries. Manifest now has {len(manifest)} total.")


if __name__ == "__main__":
    main()
