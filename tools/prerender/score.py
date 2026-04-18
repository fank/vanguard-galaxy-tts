"""Acoustic scoring for synthesized WAVs.

Goal: pick the best-sounding variant from a set of N synthesis attempts without
human listening (though humans override for any failing score). We measure:

  1. duration_sanity   — chars/sec within human speech range (0.04-0.12)
  2. loudness_sanity   — RMS between -28..-14 dBFS, peak below -2 dB (no clip)
  3. edge_silence      — leading/trailing silence < 300 ms
  4. f0_range          — enough pitch variation (expressiveness)
  5. ending_trend      — matches punctuation intent:
                          "?" wants rise (+10 Hz or more)
                          "!" wants peak / emphasis
                          "." wants gentle fall (-10..-40 Hz)
  6. voicing_holes     — no long unvoiced gaps mid-sentence (catches merges)
  7. repeat_fidelity   — for lines with repeated tokens (Ha ha ha), verify
                          each repetition is distinct (syllable preservation)
"""
from __future__ import annotations
import re
import numpy as np
from dataclasses import dataclass


@dataclass
class Score:
    duration_sanity: float   # 0..1
    loudness_sanity: float   # 0..1
    edge_silence: float      # 0..1
    f0_range: float          # 0..1
    ending_trend: float      # 0..1
    voicing_holes: float     # 0..1
    repeat_fidelity: float   # 0..1 (1.0 if no repeats to check)
    total: float             # weighted average

    def summary(self) -> str:
        def bar(v):
            n = int(v * 10); return "█" * n + "·" * (10 - n)
        return (
            f"dur {bar(self.duration_sanity)}  loud {bar(self.loudness_sanity)}  "
            f"edge {bar(self.edge_silence)}  f0 {bar(self.f0_range)}  "
            f"end {bar(self.ending_trend)}  voic {bar(self.voicing_holes)}  "
            f"rep {bar(self.repeat_fidelity)}  = {self.total:.2f}"
        )


# --- helpers ----------------------------------------------------------------

def _rms_db(x: np.ndarray, frame_samples: int) -> np.ndarray:
    trimmed = x[: len(x) // frame_samples * frame_samples]
    rms = np.sqrt(np.maximum(1e-10, (trimmed.reshape(-1, frame_samples) ** 2).mean(axis=1)))
    return 20 * np.log10(rms + 1e-10)


def _voiced_mask(x: np.ndarray, sr: int, frame_ms: int = 20, silent_db: float = -40) -> np.ndarray:
    frame = int(frame_ms * sr / 1000)
    return _rms_db(x, frame) > silent_db


def _f0_trace(x: np.ndarray, sr: int, step_ms: int = 100) -> list[tuple[float, float | None]]:
    step = int(step_ms * sr / 1000)
    trace = []
    for i in range(0, len(x) - step, step):
        seg = x[i:i + step] * np.hanning(step)
        if np.sqrt((seg ** 2).mean()) < 0.02:
            trace.append((i / sr, None))
            continue
        ac = np.correlate(seg, seg, mode="full")[step - 1:]
        ac /= ac[0] + 1e-10
        lo, hi = sr // 400, sr // 80
        if hi >= len(ac):
            trace.append((i / sr, None))
            continue
        peak = lo + np.argmax(ac[lo:hi])
        f0 = sr / peak if ac[peak] > 0.3 else None
        trace.append((i / sr, f0))
    return trace


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- individual metrics -----------------------------------------------------

def score_duration(x: np.ndarray, sr: int, text: str) -> float:
    dur = len(x) / sr
    if dur <= 0 or not text.strip():
        return 0.0
    cps = len(text) / dur
    # Ideal speech rate: 10-20 chars/sec; accept 6-25
    if 10 <= cps <= 20:
        return 1.0
    if 6 <= cps <= 25:
        return 0.7
    return 0.3


def score_loudness(x: np.ndarray, sr: int) -> float:
    peak = np.abs(x).max()
    if peak < 0.01:
        return 0.0  # silent
    if peak >= 0.99:
        return 0.3  # clipping
    # RMS on voiced frames only
    voiced = _voiced_mask(x, sr)
    if not voiced.any():
        return 0.2
    frame = int(0.02 * sr)
    rms_db = _rms_db(x, frame)[: len(voiced)]
    voiced_rms = rms_db[voiced].mean()
    # Ideal -24 to -16 dBFS
    if -24 <= voiced_rms <= -14:
        return 1.0
    if -30 <= voiced_rms <= -8:
        return 0.7
    return 0.3


def score_edge_silence(x: np.ndarray, sr: int) -> float:
    voiced = _voiced_mask(x, sr)
    if not voiced.any():
        return 0.0
    first = np.argmax(voiced)
    last = len(voiced) - 1 - np.argmax(voiced[::-1])
    lead_ms = first * 20
    trail_ms = (len(voiced) - 1 - last) * 20
    # Reward quick start and tight end
    lead_score = _clamp01(1 - max(0, lead_ms - 100) / 500)
    trail_score = _clamp01(1 - max(0, trail_ms - 200) / 500)
    return (lead_score + trail_score) / 2


def score_f0_range(trace: list[tuple[float, float | None]]) -> float:
    voiced_f0 = [f for _, f in trace if f is not None]
    if len(voiced_f0) < 3:
        return 0.0
    spread = max(voiced_f0) - min(voiced_f0)
    # 20 Hz is monotone; 80+ Hz is expressive
    if spread >= 80:
        return 1.0
    if spread >= 40:
        return 0.8
    if spread >= 20:
        return 0.5
    return 0.2


def score_ending_trend(trace: list[tuple[float, float | None]], text: str) -> float:
    voiced_tail = [f for _, f in trace[-5:] if f is not None]
    if len(voiced_tail) < 2:
        return 0.3
    start_f0 = np.mean(voiced_tail[: max(1, len(voiced_tail) // 2)])
    end_f0 = np.mean(voiced_tail[-max(1, len(voiced_tail) // 2):])
    delta = end_f0 - start_f0

    last_punct = next((c for c in reversed(text.strip()) if c in "?!."), ".")
    if last_punct == "?":
        return _clamp01(delta / 30.0 + 0.2)  # rise rewarded, flat ~0.2
    if last_punct == "!":
        peak = max(voiced_tail); floor = min(voiced_tail)
        return _clamp01((peak - floor) / 40.0)
    return _clamp01(-delta / 30.0 + 0.3)  # gentle fall rewarded


def score_voicing_holes(x: np.ndarray, sr: int, text: str) -> float:
    """Penalize only gaps longer than any plausible sentence pause.

    Natural punctuation pauses are 100-500 ms. A 1+ second mid-sentence silence
    is the actual failure mode we care about (e.g. synthesis crash mid-line).
    """
    voiced = _voiced_mask(x, sr)
    if not voiced.any():
        return 0.0
    first = np.argmax(voiced)
    last = len(voiced) - 1 - np.argmax(voiced[::-1])
    mid = voiced[first:last + 1]
    longest_ms = 0
    cur = 0
    for v in mid:
        if not v:
            cur += 1
        else:
            longest_ms = max(longest_ms, cur * 20)
            cur = 0
    # Allow generous pauses — punctuation-heavy text legitimately has them.
    # Only flag gaps over 1.2 s.
    return _clamp01(1 - max(0, longest_ms - 1200) / 800)


def score_repeat_fidelity(x: np.ndarray, sr: int, text: str) -> float:
    """If text has repeated short tokens (Ha ha ha), verify audio has matching
    distinct voiced chunks. Returns 1.0 if no repeats in text."""
    # Detect repeats like "Ha ha ha" or "no no no" — backreference to group 1 once it closes.
    m = re.search(r"\b(ha|no|yes|ho|oh|ah|ugh)(?:\s+\1){2,}\b", text, re.I)
    if not m:
        return 1.0
    # Count voiced chunks in the whole audio as a proxy — if repeats merge, fewer chunks
    voiced = _voiced_mask(x, sr)
    chunks = 0
    prev = False
    for v in voiced:
        if v and not prev: chunks += 1
        prev = v
    expected_min = m.group(0).count(" ") + 1  # each repeat should be a chunk
    return _clamp01(chunks / (expected_min * 1.5))


def score_wav(x: np.ndarray, sr: int, text: str) -> Score:
    trace = _f0_trace(x, sr)
    components = {
        "duration_sanity": score_duration(x, sr, text),
        "loudness_sanity": score_loudness(x, sr),
        "edge_silence": score_edge_silence(x, sr),
        "f0_range": score_f0_range(trace),
        "ending_trend": score_ending_trend(trace, text),
        "voicing_holes": score_voicing_holes(x, sr, text),
        "repeat_fidelity": score_repeat_fidelity(x, sr, text),
    }
    weights = {
        "duration_sanity": 1.0,
        "loudness_sanity": 1.2,
        "edge_silence": 0.5,
        "f0_range": 1.0,         # expressiveness
        "ending_trend": 1.5,     # most important — user's primary complaint
        "voicing_holes": 0.5,    # lowered — natural pauses shouldn't hurt
        "repeat_fidelity": 1.5,  # catches Ha-ha-ha merge
    }
    total = sum(components[k] * weights[k] for k in components) / sum(weights.values())
    return Score(**components, total=total)
