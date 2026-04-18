#!/usr/bin/env python3
"""Render the concat-pattern lines that the v1 extractor missed.

Reads /tmp/new_captain_lines.json + /tmp/new_other_lines.json (produced
by extract_dialogue_v2.py + the diff against the current manifest).

Captain lines render × 6 presets (same SIDs as render_captain_presets.py).
Other NPCs render with their engine/voice from npc_voice_mapping.json.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import f5_engine as f5
import kokoro_engine as kokoro
from score import score_wav
from paths import MANIFEST, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel

MAPPING = Path(__file__).parent / "npc_voice_mapping.json"

CAPTAIN_PRESETS = [
    ("captain_m1", 14), ("captain_m2", 17), ("captain_m3", 25),
    ("captain_f1",  0), ("captain_f2", 20), ("captain_f3",  3),
]


def compute_key(text: str, speaker: str) -> str:
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


def render_one(text: str, speaker: str, engine: str, ref: str) -> tuple[np.ndarray, int, float]:
    if engine == "kokoro":
        sid = ref.split(":", 1)[1] if ref.startswith("kokoro:") else ref
        x, sr = kokoro.synth(text, sid)
    else:
        x, sr = f5.synth(text, ref, seed=0)
    s = score_wav(x, sr, text)
    return x, sr, s.total


def main():
    mapping = json.loads(MAPPING.read_text())
    voicemap = {a["name"]: (a["reference"], a.get("engine", "f5")) for a in mapping["assignments"]}

    manifest = json.loads(MANIFEST.read_text())

    captain_new = json.loads(Path("/tmp/new_captain_lines.json").read_text())
    other_new = json.loads(Path("/tmp/new_other_lines.json").read_text())

    # --- captain × 6 presets ---
    print(f"Rendering {len(captain_new)} captain lines × {len(CAPTAIN_PRESETS)} presets = "
          f"{len(captain_new) * len(CAPTAIN_PRESETS)} entries")
    for preset, sid in CAPTAIN_PRESETS:
        for i, line in enumerate(captain_new, 1):
            text = line["text_normalized"]
            key = compute_key(text, preset)
            if key in manifest: continue
            x, sr = kokoro.synth(text, str(sid))
            s = score_wav(x, sr, text)
            write_wav(_wav_path(preset, key), x, sr)
            encode_ogg(_wav_path(preset, key), _ogg_path(preset, key))
            manifest[key] = {
                "key": key, "speaker": preset,
                "text_normalized": text, "text_raw": line.get("text_raw", text),
                "engine": "kokoro", "voice": f"kokoro:{sid}",
                "params": {"sid": sid, "speed": 1.0},
                "score_total": s.total,
                "ogg": manifest_ogg_rel(preset, key),
                "source": "concat-delta",
            }
        print(f"  {preset}: done ({len(captain_new)} lines)")

    # --- non-captain ---
    print(f"\nRendering {len(other_new)} non-captain lines")
    skipped = 0
    for i, line in enumerate(other_new, 1):
        speaker = line["speaker"]
        if speaker.startswith("<method:"):
            skipped += 1
            continue
        text = line["text_normalized"]
        key = compute_key(text, speaker)
        if key in manifest: continue
        if speaker not in voicemap:
            print(f"  SKIP (no voice map): {speaker}")
            skipped += 1
            continue
        ref, engine = voicemap[speaker]
        try:
            x, sr, score = render_one(text, speaker, engine, ref)
        except Exception as e:
            print(f"  [{i}/{len(other_new)}] {speaker}: FAILED — {e}")
            skipped += 1
            continue
        write_wav(_wav_path(speaker, key), x, sr)
        encode_ogg(_wav_path(speaker, key), _ogg_path(speaker, key))
        params = {"sid": int(ref.split(":", 1)[1]), "speed": 1.0} if engine == "kokoro" \
            else {"seed": 0, "speed": 1.0}
        manifest[key] = {
            "key": key, "speaker": speaker, "reference": ref,
            "text_normalized": text, "text_raw": line.get("text_raw", text),
            "engine": engine, "params": params,
            "score_total": score,
            "ogg": manifest_ogg_rel(speaker, key),
            "source": "concat-delta",
        }
        print(f"  [{i:3d}/{len(other_new)}] {speaker:<20s} engine={engine} s={score:.2f}  {text[:50]!r}")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. Skipped: {skipped}. Manifest now has {len(manifest)} entries.")


if __name__ == "__main__":
    main()
