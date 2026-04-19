#!/usr/bin/env python3
"""Full-corpus renderer. Reads render_plan.json (produced by resolve_speakers.py),
synthesizes each (speaker, text) via Kokoro-direct using the NPC's mapped voice,
encodes OGG, and writes a unified manifest.

Output layout:
  prerender/<speaker>/<sha256>.ogg  — manifest-keyed OGG files
  prerender/manifest.json           — unified manifest, updated in-place

Safe to interrupt + restart: skips entries already present in the manifest.
"""
from __future__ import annotations
import json, sys, wave, subprocess, argparse, time
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro
from score import score_wav
from paths import PACK, MANIFEST, ROOT, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel

MAPPING = ROOT / "tools" / "prerender" / "npc_voice_mapping.json"


def write_wav(path: Path, samples: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav_path: Path, ogg_path: Path, quality: int = 4):
    ogg_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
         "-c:a", "libvorbis", "-q:a", str(quality), str(ogg_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Re-render everything")
    ap.add_argument("--limit", type=int, default=None, help="Only first N (testing)")
    args = ap.parse_args()

    PACK.mkdir(parents=True, exist_ok=True)

    manifest_path = MANIFEST
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    plan = json.loads((ROOT / "tools" / "prerender" / "render_plan.json").read_text())
    if args.limit:
        plan = plan[:args.limit]

    # NPC → kokoro:SID
    mapping_data = json.loads(MAPPING.read_text())
    voicemap = {a["name"]: a["reference"] for a in mapping_data["assignments"]
                if a.get("reference", "").startswith("kokoro:")}

    to_render = plan if args.all else [p for p in plan if p["key"] not in manifest]
    print(f"Total in plan: {len(plan)},  to render: {len(to_render)}")

    start = time.time()
    for i, entry in enumerate(to_render):
        key = entry["key"]
        speaker = entry["speaker"]
        norm_text = entry["text_normalized"]
        ref = voicemap.get(speaker)
        if not ref:
            print(f"[{i+1}/{len(to_render)}] {speaker}: no kokoro voice mapped, skipping")
            continue
        sid = ref.split(":", 1)[1]
        try:
            x, sr = kokoro.synth(norm_text, sid)
        except Exception as e:
            print(f"[{i+1}/{len(to_render)}] {speaker:<25s} FAILED: {e}")
            continue

        s = score_wav(x, sr, norm_text)
        wav_path = _wav_path(speaker, key)
        ogg_path = _ogg_path(speaker, key)
        write_wav(wav_path, x, sr)
        encode_ogg(wav_path, ogg_path)

        manifest[key] = {
            **entry,
            "engine": "kokoro",
            "reference": ref,
            "params": {"sid": int(sid), "speed": 1.0},
            "score_total": s.total,
            "ogg": manifest_ogg_rel(speaker, key),
        }

        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        eta_s = (len(to_render) - i - 1) / rate if rate > 0 else 0
        if (i + 1) % 10 == 0 or i == len(to_render) - 1:
            print(f"[{i+1:4d}/{len(to_render)}] {speaker[:20]:<20s} kokoro:{sid} s={s.total:.2f}  "
                  f"rate={rate:.2f}/s  eta={int(eta_s)//60}m{int(eta_s)%60:02d}s")

        if (i + 1) % 25 == 0:
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. Manifest has {len(manifest)} entries.")


if __name__ == "__main__":
    main()
