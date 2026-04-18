#!/usr/bin/env python3
"""Sample key renders and report anomalies. Complements review.py with targeted
inspection: one line per major NPC, plus 5 random samples, plus worst-scoring
across the whole pack. Output is a single digestible markdown report.
"""
from __future__ import annotations
import json, random, subprocess, tempfile, wave
from pathlib import Path
from collections import defaultdict
import numpy as np

ROOT = Path("/home/fank/repo/vanguard-galaxy")
PACK = ROOT / "prerender" / "echo"


def decode_ogg(path: Path) -> tuple[np.ndarray, int]:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
        wav_path = t.name
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path),
                    "-ac", "1", "-ar", "24000", wav_path], check=True)
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    Path(wav_path).unlink(missing_ok=True)
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768, sr


def describe(entry: dict) -> dict:
    ogg = PACK / entry.get("ogg", f"{entry.get('key','')}.ogg")
    if not ogg.exists():
        return {"error": "ogg missing"}
    x, sr = decode_ogg(ogg)
    dur = len(x) / sr
    peak = float(np.abs(x).max())
    # Simple measurements
    frame = int(0.02 * sr)
    rms = np.sqrt(np.maximum(1e-10, (x[:len(x)//frame*frame].reshape(-1, frame)**2).mean(axis=1)))
    db_mean = 20 * np.log10(rms.mean() + 1e-10)
    silent_frac = (20*np.log10(rms + 1e-10) < -40).mean()
    return {
        "duration": round(dur, 2),
        "peak": round(peak, 2),
        "rms_db": round(float(db_mean), 1),
        "silent_frac": round(float(silent_frac), 2),
    }


def main():
    manifest_path = PACK / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    entries = list(manifest.values())
    # Normalize score field (old ECHO entries use score.total, new use score_total)
    for e in entries:
        if "score_total" not in e:
            e["score_total"] = e.get("score", {}).get("total", 0.0)

    lines = ["# Full pack spot-check\n"]
    lines.append(f"**Total entries:** {len(entries)}\n")
    by_spk = defaultdict(list)
    for e in entries:
        by_spk[e.get("speaker","?")].append(e)
    lines.append(f"**Speakers:** {len(by_spk)}\n")

    # Score histogram
    scores = [e["score_total"] for e in entries if e.get("score_total") is not None]
    lines.append("\n## Score distribution\n\n")
    lines.append(f"- Perfect (1.00):        {sum(1 for s in scores if s == 1.00)}\n")
    lines.append(f"- Excellent (≥0.95):     {sum(1 for s in scores if s >= 0.95)}\n")
    lines.append(f"- Good (≥0.85):          {sum(1 for s in scores if s >= 0.85)}\n")
    lines.append(f"- Mid (0.70-0.85):       {sum(1 for s in scores if 0.70 <= s < 0.85)}\n")
    lines.append(f"- Low (<0.70):           {sum(1 for s in scores if s < 0.70)}\n")
    lines.append(f"- avg {sum(scores)/len(scores):.3f}, min {min(scores):.2f}, max {max(scores):.2f}\n")

    # Bottom 10 lines
    bottom = sorted(entries, key=lambda e: e["score_total"])[:12]
    lines.append("\n## Worst-scoring 12 lines\n\n")
    for e in bottom:
        lines.append(f"- **{e.get('speaker','?')}** (s={e['score_total']:.2f}): "
                     f"`{e.get('text_raw','?')[:120]}`\n")

    # One sample per major speaker (≥5 lines)
    lines.append("\n## Representative sample — one line per major speaker\n\n")
    major = [(sp, es) for sp, es in by_spk.items() if len(es) >= 5]
    major.sort(key=lambda x: -len(x[1]))
    for sp, es in major[:30]:
        # Pick the median-scoring line as representative
        es_sorted = sorted(es, key=lambda e: e["score_total"])
        sample = es_sorted[len(es_sorted)//2]
        desc = describe(sample)
        avg = sum(e["score_total"] for e in es) / len(es)
        lines.append(f"### {sp}  ({len(es)} lines, avg score {avg:.2f})\n\n")
        lines.append(f"- Sample: `{sample.get('text_raw','?')[:120]}`\n")
        lines.append(f"- Score: {sample['score_total']:.2f}\n")
        lines.append(f"- Reference: `{sample.get('reference','?')}`\n")
        lines.append(f"- Audio: {desc.get('duration', '?')}s, peak {desc.get('peak', '?')}, "
                     f"RMS {desc.get('rms_db', '?')} dB\n\n")

    # Random 5 from the whole pack
    random.seed(42)
    lines.append("\n## Random sample (deterministic)\n\n")
    for e in random.sample(entries, min(8, len(entries))):
        desc = describe(e)
        lines.append(f"- **{e.get('speaker','?')}** (s={e['score_total']:.2f}): "
                     f"`{e.get('text_raw','?')[:100]}`\n")
        lines.append(f"  ref={e.get('reference','?')}  dur={desc.get('duration', '?')}s  peak={desc.get('peak', '?')}\n")

    # Missing / failed
    failed = [e for e in entries if e.get("status") == "failed"]
    lines.append(f"\n## Failures: {len(failed)}\n\n")
    for e in failed[:10]:
        lines.append(f"- {e.get('speaker')}: {e.get('error','?')[:200]}\n")

    report_path = PACK / "spot_check.md"
    report_path.write_text("".join(lines))
    print(f"Wrote {report_path}")
    print(f"Pack has {len(entries)} entries, {len(scores)} scored, avg={sum(scores)/len(scores):.3f}")


if __name__ == "__main__":
    main()
