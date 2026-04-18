#!/usr/bin/env python3
"""Full-corpus renderer. 1172 unique (speaker, text) pairs, each with its
NPC-specific F5-TTS reference. One variant per line (retry losers later).

Output layout identical to the ECHO pack so plugin's PrerenderLookup
transparently finds both:
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
import f5_engine as f5
from score import score_wav
from paths import PACK, MANIFEST, ROOT, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel


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
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--only-missing", action="store_true", default=True,
                    help="Skip entries already in manifest (default)")
    ap.add_argument("--all", action="store_true", help="Re-render everything")
    ap.add_argument("--limit", type=int, default=None, help="Only first N (testing)")
    args = ap.parse_args()

    PACK.mkdir(parents=True, exist_ok=True)

    manifest = {}
    manifest_path = MANIFEST
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    plan = json.loads((ROOT / "tools" / "prerender" / "render_plan.json").read_text())
    if args.limit:
        plan = plan[:args.limit]

    to_render = plan if args.all else [p for p in plan if p["key"] not in manifest]
    print(f"Total in plan: {len(plan)},  already in manifest: {len(plan)-len(to_render)},  to render: {len(to_render)}")

    start = time.time()
    for i, entry in enumerate(to_render):
        key = entry["key"]
        speaker = entry["speaker"]
        ref = entry["reference"]
        norm_text = entry["text_normalized"]

        try:
            x, sr = f5.synth(norm_text, ref, seed=args.seed)
        except Exception as e:
            print(f"[{i+1}/{len(to_render)}] {speaker:<25s} FAILED: {e}")
            manifest[key] = {
                **entry, "engine": "f5", "status": "failed",
                "error": str(e)[:200],
            }
            continue

        s = score_wav(x, sr, norm_text)

        wav_path = _wav_path(speaker, key)
        ogg_path = _ogg_path(speaker, key)
        write_wav(wav_path, x, sr)
        encode_ogg(wav_path, ogg_path)

        manifest[key] = {
            **entry,
            "engine": "f5",
            "params": {"seed": args.seed, "speed": 1.0},
            "score_total": s.total,
            "score_components": {k: v for k, v in s.__dict__.items() if k != "total"},
            "ogg": manifest_ogg_rel(speaker, key),
        }

        elapsed = time.time() - start
        rate = (i + 1) / elapsed
        eta_s = (len(to_render) - i - 1) / rate if rate > 0 else 0
        # Compact progress
        if (i + 1) % 10 == 0 or i == len(to_render) - 1:
            print(f"[{i+1:4d}/{len(to_render)}] {speaker[:20]:<20s} s={s.total:.2f}  "
                  f"rate={rate:.2f}/s  eta={int(eta_s)//60}m{int(eta_s)%60:02d}s")

        # Periodic manifest save so a crash doesn't cost everything
        if (i + 1) % 25 == 0:
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    elapsed = time.time() - start
    print(f"\nDone. {len(to_render)} rendered in {int(elapsed)//60}m{int(elapsed)%60:02d}s. "
          f"Manifest now has {len(manifest)} entries.")


if __name__ == "__main__":
    main()
