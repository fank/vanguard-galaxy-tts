#!/usr/bin/env python3
"""End-to-end ECHO tip renderer.

For each of 66 ECHO tips:
  1. Normalize text (ellipsis → pauses, etc.)
  2. Generate N variants (different speeds / speakers / seeds)
  3. Score each variant acoustically
  4. Select best; encode OGG
  5. Append to manifest

Writes:
  prerender/echo/<key>.ogg      — one file per tip
  prerender/echo/manifest.json  — key → metadata (text, speaker, score, engine, ...)
  prerender/echo/variants/      — all attempts (for debug / review)
  prerender/echo/review.tsv     — lines needing manual review (low scores)
"""
from __future__ import annotations
import argparse, json, wave, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from normalize import for_tts, prerender_key  # noqa: E402
from score import score_wav                   # noqa: E402

ROOT = Path("/home/fank/repo/vanguard-galaxy")
OUTDIR = ROOT / "prerender" / "echo"
VARDIR = OUTDIR / "variants"
TIPS_PATH = ROOT / "tools" / "prerender" / "echo_tips.json"
SPEAKER = "ECHO"


def write_wav(path: Path, samples: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav_path: Path, ogg_path: Path, quality: int = 4):
    """Transcode WAV → OGG Vorbis using ffmpeg if available."""
    import subprocess
    ogg_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-c:a", "libvorbis", "-q:a", str(quality), str(ogg_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-500:]}")


def render_one(engine, text: str, voice: str, variants: list[dict]) -> list[tuple[dict, np.ndarray, int, object]]:
    """Generate all variants. Returns list of (params, samples, sr, score)."""
    out = []
    for params in variants:
        try:
            x, sr = engine.synth(text, voice, **params)
        except Exception as e:
            print(f"    variant {params} failed: {e}")
            continue
        s = score_wav(x, sr, text)
        out.append((params, x, sr, s))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["kokoro", "f5"], default="kokoro")
    ap.add_argument("--voice", required=True, help="engine-specific voice id")
    ap.add_argument("--keys", nargs="*", help="specific tip keys to render (default: all)")
    ap.add_argument("--variants", type=int, default=3, help="variants per line")
    args = ap.parse_args()

    if args.engine == "kokoro":
        from engines import kokoro_engine as engine
    else:
        from engines import f5_engine as engine

    tips = json.loads(TIPS_PATH.read_text())
    if args.keys:
        tips = {k: tips[k] for k in args.keys if k in tips}
    print(f"Rendering {len(tips)} tips with {args.engine}:{args.voice}")

    # Variant matrix — differs slightly per engine
    variant_params = []
    if args.engine == "kokoro":
        for speed in (0.95, 1.00, 1.05)[:args.variants]:
            variant_params.append({"speed": speed})
    else:  # f5
        for seed in range(args.variants):
            variant_params.append({"seed": seed, "speed": 1.0})

    OUTDIR.mkdir(parents=True, exist_ok=True)
    VARDIR.mkdir(parents=True, exist_ok=True)

    manifest = {}
    if (OUTDIR / "manifest.json").exists():
        manifest = json.loads((OUTDIR / "manifest.json").read_text())

    review = []

    for i, (tip_id, raw_text) in enumerate(sorted(tips.items())):
        raw_text = raw_text.strip()  # strip CR/LF from .ini loader
        norm = for_tts(raw_text)
        key = prerender_key(raw_text, SPEAKER)
        print(f"[{i+1:2d}/{len(tips)}] {tip_id:>25s}  {norm[:70]}")
        attempts = render_one(engine, norm, args.voice, variant_params)
        if not attempts:
            print(f"    ALL VARIANTS FAILED")
            review.append((tip_id, "all_failed", raw_text))
            continue

        attempts.sort(key=lambda a: -a[3].total)
        best_params, best_x, best_sr, best_score = attempts[0]
        print(f"    best: {best_score.summary()}  params={best_params}")

        # Save best as WAV then encode to OGG
        wav_path = VARDIR / f"{tip_id}_best.wav"
        ogg_path = OUTDIR / f"{key}.ogg"
        write_wav(wav_path, best_x, best_sr)
        encode_ogg(wav_path, ogg_path)

        # Also keep all variants for possible manual review
        for j, (params, x, sr, s) in enumerate(attempts):
            write_wav(VARDIR / f"{tip_id}_v{j}_total{s.total:.2f}.wav", x, sr)

        manifest[key] = {
            "tip_id": tip_id,
            "text_raw": raw_text,
            "text_normalized": norm,
            "speaker": SPEAKER,
            "engine": args.engine,
            "voice": args.voice,
            "voice_name": engine.speaker_name(args.voice),
            "params": best_params,
            "score": {
                "total": best_score.total,
                "components": best_score.__dict__,
            },
            "ogg": f"{key}.ogg",
        }

        if best_score.total < 0.55:
            review.append((tip_id, f"low_score_{best_score.total:.2f}", raw_text))

    (OUTDIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    if review:
        (OUTDIR / "review.tsv").write_text(
            "tip_id\treason\ttext\n" + "\n".join("\t".join(r) for r in review)
        )
        print(f"\n{len(review)} lines flagged for review — see prerender/echo/review.tsv")
    print(f"\nDone. {len(manifest)} lines in manifest at prerender/echo/manifest.json")


if __name__ == "__main__":
    main()
