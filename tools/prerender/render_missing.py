#!/usr/bin/env python3
"""Delta renderer — reads the plugin's runtime miss log and renders any new lines.

Source file is written by the in-game plugin at:
  <game>/BepInEx/cache/VGTTS/unprerendered.tsv

Each row: isoTimestamp\\tspeaker\\tnormalized_text\\tsha256key

For every row not already in the shipped manifest, we synth with Kokoro-direct
using the NPC's mapped voice from npc_voice_mapping.json, encode OGG, and
append to the manifest. Safe to re-run; skips entries already present.

Typical flow after a game patch adds new dialogue:
    cp "$STEAM_GAME/BepInEx/cache/VGTTS/unprerendered.tsv" .
    python tools/prerender/render_missing.py --input unprerendered.tsv
    git add prerender/ && git commit -m "chore: render delta from patch X"
"""
from __future__ import annotations
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro
from score import score_wav
from paths import MANIFEST, ROOT, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel

MAPPING = ROOT / "tools" / "prerender" / "npc_voice_mapping.json"


def unescape(s: str) -> str:
    return (s.replace("\\t", "\t").replace("\\n", "\n")
             .replace("\\r", "\r").replace("\\\\", "\\"))


def write_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav_path: Path, ogg_path: Path, q: int = 4):
    ogg_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
         "-c:a", "libvorbis", "-q:a", str(q), str(ogg_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="path to unprerendered.tsv")
    args = ap.parse_args()

    mapping_data = json.loads(MAPPING.read_text())
    # speaker → kokoro:SID string
    voicemap: dict[str, str] = {}
    for a in mapping_data["assignments"]:
        ref = a.get("reference", "")
        if ref.startswith("kokoro:"):
            voicemap[a["name"]] = ref
    default_voice = voicemap.get("captain_m1", "kokoro:14")

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    rows = []
    for line in Path(args.input).read_text().splitlines():
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if len(parts) < 4: continue
        _, speaker, text, key = parts[0], unescape(parts[1]), unescape(parts[2]), parts[3]
        if key in manifest: continue
        rows.append((key, speaker, text))

    print(f"{len(rows)} new lines to render (manifest has {len(manifest)} already)")

    for i, (key, speaker, text) in enumerate(rows):
        ref = voicemap.get(speaker, default_voice)
        sid = ref.split(":", 1)[1]
        try:
            x, sr = kokoro.synth(text, sid)
        except Exception as e:
            print(f"[{i+1}/{len(rows)}] {speaker}: Kokoro synth failed: {e}")
            continue
        s = score_wav(x, sr, text)

        wav_path = _wav_path(speaker, key)
        ogg_path = _ogg_path(speaker, key)
        write_wav(wav_path, x, sr)
        encode_ogg(wav_path, ogg_path)
        manifest[key] = {
            "text_raw": text, "text_normalized": text,
            "speaker": speaker,
            "engine": "kokoro", "reference": ref,
            "params": {"sid": int(sid), "speed": 1.0},
            "score_total": s.total,
            "source": "delta-render",
            "ogg": manifest_ogg_rel(speaker, key),
        }
        print(f"[{i+1}/{len(rows)}] {speaker:<25s} kokoro:{sid}  s={s.total:.2f}")
        if (i + 1) % 20 == 0:
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. Manifest now has {len(manifest)} entries.")


if __name__ == "__main__":
    main()
