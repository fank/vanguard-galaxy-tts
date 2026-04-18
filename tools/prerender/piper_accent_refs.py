#!/usr/bin/env python3
"""Generate English-probe renders via Piper's non-English speakers. Save each
as an F5-TTS reference (WAV + transcript) so F5 can clone the accent onto
any text we render later.

Uses the Python Piper API directly — no shell-out to Windows piper.exe."""
from __future__ import annotations
from pathlib import Path
import wave

from piper import PiperVoice

VOICES_DIR = Path("/home/fank/repo/vanguard-galaxy/tools/voices")
REF_DIR = Path("/home/fank/repo/vanguard-galaxy/tools/prerender/references")
REF_DIR.mkdir(parents=True, exist_ok=True)

# The same probe text used for Kokoro refs so everything is comparable.
PROBE = "The ship is ready for launch. Proceed when you are prepared."

VOICES = [
    ("en_GB-alba-medium",              "en_GB_alba_scottish"),
    ("ru_RU-dmitri-medium",            "ru_RU_dmitri"),
    ("ru_RU-denis-medium",             "ru_RU_denis"),
    ("de_DE-thorsten_emotional-medium","de_DE_thorsten_emotional"),
    ("sv_SE-alma-medium",              "sv_SE_alma"),
]


def synth_piper(voice_name: str, text: str, out_wav: Path):
    model_path = VOICES_DIR / f"{voice_name}.onnx"
    cfg_path = VOICES_DIR / f"{voice_name}.onnx.json"
    voice = PiperVoice.load(str(model_path), config_path=str(cfg_path))

    # Piper streams WAV PCM. Write via wave module so we can control headers.
    with wave.open(str(out_wav), "wb") as wav_file:
        # Placeholder header — Piper synthesize_wav sets params as it writes.
        # Some versions expose synthesize() returning AudioChunk — use the API
        # that supports both.
        # Modern piper-tts: voice.synthesize(text, wav_file)
        try:
            voice.synthesize_wav(text, wav_file)
        except AttributeError:
            for chunk in voice.synthesize(text):
                # chunk has .audio_int16_bytes + .sample_rate/.sample_width/.sample_channels
                if wav_file.getnchannels() == 0:
                    wav_file.setnchannels(chunk.sample_channels)
                    wav_file.setsampwidth(chunk.sample_width)
                    wav_file.setframerate(chunk.sample_rate)
                wav_file.writeframes(chunk.audio_int16_bytes)


for voice_name, ref_name in VOICES:
    out = REF_DIR / f"{ref_name}.wav"
    print(f"Rendering {voice_name} -> {out.name}")
    synth_piper(voice_name, PROBE, out)
    (REF_DIR / f"{ref_name}.txt").write_text(PROBE)
    size = out.stat().st_size
    print(f"  ok: {size/1024:.0f} KB")

print(f"\nAdded {len(VOICES)} accent references to {REF_DIR}")
