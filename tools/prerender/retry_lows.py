#!/usr/bin/env python3
"""Retry low-scoring lines with more seeds. Keeps the best of all attempts.

Run after render_full.py completes. Pulls the 5% worst lines and retries each
with 5 additional seeds, picking the best score across old + new. Updates the
manifest + OGG file in-place.
"""
from __future__ import annotations
import json, sys, wave, subprocess
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import f5_engine as f5
from score import score_wav
from paths import MANIFEST, ogg_path as _ogg_path, wav_path as _wav_path


def write_wav(path, x, sr):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav_path, ogg_path, q=4):
    ogg_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav_path),
         "-c:a", "libvorbis", "-q:a", str(q), str(ogg_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-200:]}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.80)
    ap.add_argument("--extra-seeds", type=int, default=5)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    # Pick low-scorers
    low = []
    for key, e in manifest.items():
        s = e.get("score_total")
        if s is None:
            s = e.get("score", {}).get("total")
        if s is None or s >= args.threshold:
            continue
        low.append((key, e, s))
    low.sort(key=lambda x: x[2])
    print(f"Retrying {len(low)} lines below {args.threshold}")

    improved = 0
    for key, entry, old_score in low:
        norm_text = entry.get("text_normalized") or entry.get("text_raw", "")
        ref = entry.get("reference")
        if not ref or not norm_text:
            continue
        best = (old_score, None, None)  # (score, samples, sr)
        for seed in range(entry.get("params", {}).get("seed", 0) + 1,
                          entry.get("params", {}).get("seed", 0) + 1 + args.extra_seeds):
            try:
                x, sr = f5.synth(norm_text, ref, seed=seed)
            except Exception:
                continue
            s = score_wav(x, sr, norm_text)
            if s.total > best[0]:
                best = (s.total, x, sr, seed, s)
        if best[1] is not None and best[0] > old_score:
            # Save new best
            speaker = entry.get("speaker", "_unknown")
            wav_path = _wav_path(speaker, key)
            ogg_path = _ogg_path(speaker, key)
            write_wav(wav_path, best[1], best[2])
            encode_ogg(wav_path, ogg_path)
            entry["score_total"] = best[0]
            entry["score_components"] = {k: v for k, v in best[4].__dict__.items() if k != "total"}
            entry["params"] = {"seed": best[3], "speed": 1.0}
            improved += 1
            print(f"  {entry.get('speaker','?'):<25s} {old_score:.2f} -> {best[0]:.2f}  seed={best[3]}")

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nImproved {improved} / {len(low)} low-scoring lines")


if __name__ == "__main__":
    main()
