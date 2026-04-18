#!/usr/bin/env python3
"""Post-render quality review. Loads the manifest, scores every rendered line
(on final OGG, not WAV variants), produces a human-readable report with flags.

Runs automated checks that approximate 'listening':
- F0 rise/fall matches final punctuation
- No clipping, good loudness
- Duration makes sense for text length
- For lines with specific hard patterns, targeted checks

Output:
  prerender/review_report.md
  prerender/review_report.json
"""
from __future__ import annotations
import json, re, subprocess, sys
from pathlib import Path
import numpy as np, wave

sys.path.insert(0, str(Path(__file__).parent))
from score import score_wav, _f0_trace  # noqa: E402
from paths import PACK, MANIFEST  # noqa: E402


def load_ogg_as_pcm(path: Path) -> tuple[np.ndarray, int]:
    """Decode OGG via ffmpeg to 16-bit PCM WAV for analysis."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "24000", wav_path],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg decode failed: {r.stderr}")
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    os.unlink(wav_path)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    return x, sr


def analyze_entry(key: str, entry: dict) -> dict:
    # The manifest's `ogg` field is a relative path like "<speaker>/<sha>.ogg".
    ogg = PACK / entry.get("ogg", f"{key}.ogg")
    text = entry.get("text_normalized") or entry.get("text_raw", "")
    raw_text = entry.get("text_raw", text)
    if not ogg.exists():
        return {"key": key, "tip_id": entry.get("tip_id") or entry.get("speaker","?"),
                "text": raw_text, "normalized": text, "flags": ["MISSING_OGG"],
                "score_total": 0.0, "score_components": {}}
    x, sr = load_ogg_as_pcm(ogg)
    s = score_wav(x, sr, text)
    trace = _f0_trace(x, sr)
    voiced = [f for _, f in trace if f is not None]
    tail = [f for _, f in trace[-5:] if f is not None]
    flags = []
    last_p = next((c for c in reversed(text.strip()) if c in "?!."), ".")
    if last_p == "?" and len(tail) >= 2:
        delta = tail[-1] - tail[0]
        if delta < 10:
            flags.append(f"NO_RISE({delta:+.0f}Hz)")
    if last_p == "!" and len(voiced) >= 3:
        if max(voiced) - min(voiced) < 30:
            flags.append("NO_EMPHASIS")
    if np.abs(x).max() > 0.99:
        flags.append("CLIP")
    if np.abs(x).max() < 0.1:
        flags.append("QUIET")
    if re.search(r"\b(ha|no|yes|oh|ah)(\s+\1){2,}\b", raw_text, re.I):
        # Count voiced chunks in the target segment — heuristic
        rf = s.repeat_fidelity
        if rf < 0.7:
            flags.append(f"REPEAT_MERGE({rf:.2f})")
    if s.total < 0.55:
        flags.append(f"LOW_SCORE({s.total:.2f})")
    dur = len(x) / sr
    cps = len(text) / dur if dur > 0 else 0
    if cps < 6 or cps > 25:
        flags.append(f"CPS_ODD({cps:.1f})")
    return {
        "key": key,
        "tip_id": entry.get("tip_id") or entry.get("speaker", "?"),
        "speaker": entry.get("speaker", "?"),
        "text": raw_text,
        "normalized": text,
        "duration": dur,
        "cps": cps,
        "peak": float(np.abs(x).max()),
        "f0_tail_start": tail[0] if tail else None,
        "f0_tail_end": tail[-1] if tail else None,
        "f0_delta": (tail[-1] - tail[0]) if len(tail) >= 2 else None,
        "score_total": s.total,
        "score_components": {k: v for k, v in s.__dict__.items() if k != "total"},
        "flags": flags,
    }


def main():
    manifest = json.loads(MANIFEST.read_text())
    print(f"Reviewing {len(manifest)} entries...")
    rows = []
    for i, (key, entry) in enumerate(manifest.items()):
        r = analyze_entry(key, entry)
        rows.append(r)
        flag_str = " ".join(r["flags"]) if r["flags"] else "ok"
        print(f"  [{i+1:2d}/{len(manifest)}] {r['tip_id']:>25s}  s={r['score_total']:.2f}  {flag_str}")

    # Sort by flags (worst first) then by score ascending
    rows.sort(key=lambda r: (-len(r["flags"]), r["score_total"]))

    report_md = ["# ECHO Prerender Review\n"]
    report_md.append(f"Total lines: {len(rows)}\n")
    flagged = [r for r in rows if r["flags"]]
    report_md.append(f"Flagged for manual review: {len(flagged)}\n\n")

    # Flags summary
    flag_counter: dict[str, int] = {}
    for r in rows:
        for f in r["flags"]:
            bucket = f.split("(")[0]
            flag_counter[bucket] = flag_counter.get(bucket, 0) + 1
    report_md.append("## Flag distribution\n\n")
    for f, n in sorted(flag_counter.items(), key=lambda kv: -kv[1]):
        report_md.append(f"- {f}: {n}\n")
    report_md.append("\n")

    # Problem lines
    report_md.append("## Flagged lines\n\n")
    for r in flagged:
        flag_str = " ".join(r["flags"])
        report_md.append(f"### {r['tip_id']}  ({flag_str})\n\n")
        report_md.append(f"- Text: `{r['text']}`\n")
        report_md.append(f"- Normalized: `{r['normalized']}`\n")
        report_md.append(f"- Duration: {r['duration']:.2f}s, CPS: {r['cps']:.1f}, Peak: {r['peak']:.2f}\n")
        if r["f0_delta"] is not None:
            report_md.append(f"- F0 tail: {r['f0_tail_start']:.0f} → {r['f0_tail_end']:.0f} Hz (Δ={r['f0_delta']:+.0f})\n")
        report_md.append(f"- Score: {r['score_total']:.2f}\n\n")

    report_md.append("## All lines (ranked)\n\n")
    report_md.append("| tip_id | score | dur | Δf0 | flags | text |\n|---|---|---|---|---|---|\n")
    for r in rows:
        df0 = f"{r['f0_delta']:+.0f}" if r["f0_delta"] is not None else "—"
        flg = " ".join(r["flags"]) if r["flags"] else ""
        txt = r["text"][:80].replace("|", "\\|")
        report_md.append(f"| {r['tip_id']} | {r['score_total']:.2f} | {r['duration']:.1f}s | {df0} | {flg} | {txt} |\n")

    (PACK / "review_report.md").write_text("".join(report_md))
    (PACK / "review_report.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"\nReport: {PACK/'review_report.md'}")
    print(f"Flagged: {len(flagged)} / {len(rows)}")


if __name__ == "__main__":
    main()
