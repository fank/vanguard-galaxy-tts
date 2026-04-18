#!/usr/bin/env python3
"""Delta renderer — reads the plugin's runtime miss log and renders any new lines.

Source file is written by the in-game plugin at:
  <game>/BepInEx/cache/VGTTS/unprerendered.tsv

Each row: isoTimestamp\\tspeaker\\tnormalized_text\\tsha256key

For every row not already in the shipped manifest, we synth with F5-TTS
(using the NPC's mapped reference), score, encode OGG, and append to the
manifest. Safe to re-run; skips entries already present.

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
import f5_engine as f5
from score import score_wav

ROOT   = Path("/home/fank/repo/vanguard-galaxy")
PACK   = ROOT / "prerender" / "echo"
VARDIR = PACK / "variants"
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
    ap.add_argument("--seeds", type=int, default=3, help="variants per line")
    args = ap.parse_args()

    mapping_data = json.loads(MAPPING.read_text())
    refmap = {a["name"]: a["reference"] for a in mapping_data["assignments"]}
    default_ref = refmap.get("captain", "kokoro_af_sky_10")

    manifest_path = PACK / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    rows = []
    for line in Path(args.input).read_text().splitlines():
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if len(parts) < 4: continue
        _, speaker, text, key = parts[0], unescape(parts[1]), unescape(parts[2]), parts[3]
        if key in manifest: continue  # already rendered
        rows.append((key, speaker, text))

    print(f"{len(rows)} new lines to render (input had ? entries, "
          f"manifest has {len(manifest)} already)")

    for i, (key, speaker, text) in enumerate(rows):
        ref = refmap.get(speaker, default_ref)
        best = (0.0, None, None, None)
        for seed in range(args.seeds):
            try:
                x, sr = f5.synth(text, ref, seed=seed)
                s = score_wav(x, sr, text)
                if s.total > best[0]:
                    best = (s.total, x, sr, seed)
            except Exception as e:
                print(f"  seed {seed} failed: {e}")
        if best[1] is None:
            print(f"[{i+1}/{len(rows)}] {speaker}: ALL VARIANTS FAILED")
            continue
        wav_path = VARDIR / f"{key}.wav"
        ogg_path = PACK / f"{key}.ogg"
        write_wav(wav_path, best[1], best[2])
        encode_ogg(wav_path, ogg_path)
        manifest[key] = {
            "key": key, "speaker": speaker, "reference": ref,
            "text_normalized": text, "text_raw": text,
            "engine": "f5", "params": {"seed": best[3], "speed": 1.0},
            "score_total": best[0],
            "ogg": f"{key}.ogg",
            "source": "delta-render",
        }
        print(f"[{i+1}/{len(rows)}] {speaker:<25s} s={best[0]:.2f}  seed={best[3]}")
        if (i + 1) % 20 == 0:
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. Manifest now has {len(manifest)} entries.")


if __name__ == "__main__":
    main()
