#!/usr/bin/env python3
"""Re-render all ECHO lines with Kokoro-direct + af_aoede (SID 1).

Switches ECHO from F5-cloned bf_emma (fragment-prone) to native Kokoro
synthesis — smoother for the 200th playback. The cache key is
sha256(text, speaker) so OGG filenames don't change; we just overwrite
content and rewrite the manifest entry's engine/voice fields.
"""
from __future__ import annotations
import json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "engines"))
import kokoro_engine as kokoro
from score import score_wav
from paths import MANIFEST, ogg_path as _ogg_path, wav_path as _wav_path, manifest_ogg_rel

ECHO_VOICE_SID = 1       # af_aoede
ECHO_VOICE_NAME = "kokoro:1"  # how the plugin/mapping will reference it


def write_wav(path: Path, x: np.ndarray, sr: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def encode_ogg(wav: Path, ogg: Path, q: int = 4):
    ogg.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(wav),
         "-c:a", "libvorbis", "-q:a", str(q), str(ogg)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr[-300:]}")


def main():
    manifest = json.loads(MANIFEST.read_text())
    echo_keys = [k for k, e in manifest.items() if e.get("speaker") == "ECHO"]
    print(f"Re-rendering {len(echo_keys)} ECHO lines with Kokoro af_aoede (SID {ECHO_VOICE_SID})\n")

    for i, key in enumerate(echo_keys, 1):
        entry = manifest[key]
        text = entry.get("text_normalized") or entry.get("text_raw") or ""
        if not text:
            print(f"[{i:3d}/{len(echo_keys)}] {key[:12]}: MISSING TEXT, skipping")
            continue

        x, sr = kokoro.synth(text, str(ECHO_VOICE_SID))
        s = score_wav(x, sr, text)

        speaker = entry.get("speaker", "ECHO")
        wav_path = _wav_path(speaker, key)
        ogg_path = _ogg_path(speaker, key)
        write_wav(wav_path, x, sr)
        encode_ogg(wav_path, ogg_path)

        # Update manifest entry — keep key/text/speaker, swap engine+voice+score+ogg path
        entry.update({
            "engine": "kokoro",
            "voice": ECHO_VOICE_NAME,
            "voice_name": "kokoro_af_aoede_1",
            "reference": None,   # Kokoro-direct has no F5 reference
            "params": {"sid": ECHO_VOICE_SID, "speed": 1.0},
            "score_total": s.total,
            "ogg": manifest_ogg_rel(speaker, key),
            "source": "kokoro-direct-rerender",
        })
        # Drop obsolete F5-era fields
        entry.pop("score", None)
        entry.pop("tip_id", None)

        print(f"[{i:3d}/{len(echo_keys)}] {key[:12]}  dur={len(x)/sr:.2f}s  score={s.total:.2f}")

        # Checkpoint manifest every 40 lines
        if i % 40 == 0:
            MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"\nDone. Manifest saved ({len(manifest)} total entries).")


if __name__ == "__main__":
    main()
