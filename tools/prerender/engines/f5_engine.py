"""F5-TTS backend. Voice-clones from a reference WAV + transcript.

Quality ceiling is the reference audio — a good reference produces top-tier output.
Works best with 6-15 seconds of clean speech from the target voice.

Voice id format: name of a reference preset (files in tools/prerender/references/).
Each preset has <name>.wav + <name>.txt (the transcript). The special voice
name "default_en" uses F5-TTS's bundled English reference.
"""
from __future__ import annotations
import numpy as np
from pathlib import Path

_REFS = Path("/home/fank/repo/vanguard-galaxy/tools/prerender/references")
_BUILTIN_EN_WAV = Path(
    "/home/fank/vgtts-env/lib/python3.12/site-packages/f5_tts/infer/examples/basic/basic_ref_en.wav"
)
_BUILTIN_EN_TEXT = "Some call me nature, others call me mother nature."

_model = None


def _load():
    global _model
    if _model is not None:
        return _model
    from f5_tts.api import F5TTS
    _model = F5TTS(model="F5TTS_v1_Base", device=None)
    return _model


def _resolve_ref(voice: str) -> tuple[str, str]:
    if voice == "default_en":
        return str(_BUILTIN_EN_WAV), _BUILTIN_EN_TEXT
    ref_wav = _REFS / f"{voice}.wav"
    ref_txt = _REFS / f"{voice}.txt"
    if not ref_wav.exists() or not ref_txt.exists():
        raise FileNotFoundError(f"F5 reference '{voice}' missing at {_REFS}")
    return str(ref_wav), ref_txt.read_text().strip()


def _post_process(wav: np.ndarray, sr: int) -> np.ndarray:
    """Normalize peak + trim generous edge silence F5 sometimes emits."""
    wav = np.asarray(wav, dtype=np.float32)
    # Peak-normalize to -1 dBFS (0.89) so AudioSource doesn't hit digital clip.
    peak = np.abs(wav).max()
    if peak > 0.001:
        wav = wav * (0.89 / peak)
    # Trim silence below -40 dBFS at edges, preserving 80 ms of padding
    silence = np.abs(wav) < 0.01
    nz = np.where(~silence)[0]
    if len(nz) == 0:
        return wav
    pad = int(0.08 * sr)
    start = max(0, nz[0] - pad)
    end = min(len(wav), nz[-1] + pad)
    return wav[start:end]


def synth(text: str, voice: str, seed: int | None = None, speed: float = 1.0,
          nfe_step: int = 32):
    ref_wav, ref_text = _resolve_ref(voice)
    model = _load()
    wav, sr, _ = model.infer(
        ref_file=ref_wav,
        ref_text=ref_text,
        gen_text=text,
        speed=speed,
        seed=seed,
        nfe_step=nfe_step,       # 32 = default quality; 16 faster, 64 higher
        cross_fade_duration=0.15,
        remove_silence=False,
        target_rms=0.1,
        cfg_strength=2.0,
    )
    return _post_process(wav, sr), sr


def speaker_name(voice: str) -> str:
    return voice
