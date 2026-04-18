#!/usr/bin/env python3
"""Side-by-side voice shootout.

Renders a handful of representative ECHO lines with each reference voice,
scores each, writes a comparison table so we can pick the best reference for
the full render.

Representative line selection:
- One pure question (tests F0 rise)
- One pure exclamation (tests emphasis)
- One statement (tests baseline delivery)
- One long multi-sentence (tests stamina)
- The hard laugh+binary line (tests edge case)
"""
from __future__ import annotations
import sys, wave, numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import f5_engine as f5
from score import score_wav, _f0_trace
from normalize import for_tts

OUT = Path(__file__).parent.parent.parent / "prerender" / "shootout"
OUT.mkdir(parents=True, exist_ok=True)

SAMPLE_LINES = {
    "question":    "Did you know that mining lasers mine asteroids? I know right? Nuts!",
    "exclamation": "This music takes me places!",
    "statement":   "The core of an asteroid is quite valuable. And I like credits.",
    "longform":    "Sometimes I just want to forget myself and fly into the sun... Its so pretty!",
    "ha_binary":   "00101101011... Ha ha ha! Hey, why are you not laughing?",
}

REFS = [
    "default_en",
    "kokoro_bf_emma_21",
    "kokoro_bf_isabella_22",
    "kokoro_af_nova_7",
    "kokoro_af_jessica_4",
    "kokoro_af_sky_10",
]


def save(path: Path, x, sr):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def main():
    import json
    rows = []
    for label, text in SAMPLE_LINES.items():
        norm = for_tts(text)
        for ref in REFS:
            print(f"[{label}/{ref}]")
            try:
                x, sr = f5.synth(norm, ref, seed=0)
            except Exception as e:
                print(f"  FAILED: {e}")
                continue
            s = score_wav(x, sr, norm)
            trace = _f0_trace(x, sr); tail = [f for _, f in trace[-5:] if f is not None]
            d = (tail[-1] - tail[0]) if len(tail) >= 2 else None
            save(OUT / f"{label}__{ref}.wav", x, sr)
            rows.append({
                "line": label, "ref": ref, "duration": len(x)/sr,
                "peak": float(np.abs(x).max()), "score": s.total,
                "f0_delta": d, "flags": [],
            })
            print(f"  dur={len(x)/sr:.2f}s peak={np.abs(x).max():.2f} "
                  f"Δf0={d if d is None else f'{d:+.0f}'} score={s.total:.2f}")

    # Build comparison per line
    print("\n=== Summary ===\n")
    by_line = {}
    for r in rows:
        by_line.setdefault(r["line"], []).append(r)
    print(f"{'line':<12s} | best ref                       | Δf0   | score")
    for line, rs in by_line.items():
        rs.sort(key=lambda r: -r["score"])
        best = rs[0]
        d = f"{best['f0_delta']:+.0f}" if best['f0_delta'] is not None else "—"
        print(f"{line:<12s} | {best['ref']:<30s} | {d:>5s} | {best['score']:.2f}")

    # Aggregate score per ref
    ref_totals = {}
    for r in rows:
        ref_totals.setdefault(r["ref"], []).append(r["score"])
    print(f"\nAverage score per reference:")
    for ref, scores in sorted(ref_totals.items(), key=lambda kv: -sum(kv[1])/len(kv[1])):
        print(f"  {ref:<30s} avg={sum(scores)/len(scores):.2f} (n={len(scores)})")

    (OUT / "shootout_results.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"\nSaved WAVs + JSON in {OUT}")


if __name__ == "__main__":
    main()
