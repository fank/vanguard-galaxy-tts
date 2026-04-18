"""Kokoro backend via sherpa-onnx. Known-good quality baseline; rendering target
for the 'free local, no GPU' fallback.

Voice id format: integer speaker ID in 0-52 (matching our bundle's v1.0 model).
"""
from __future__ import annotations
import numpy as np
from pathlib import Path

_BUNDLE = Path("/home/fank/repo/vanguard-galaxy/tools/kokoro")
_tts = None


def _load():
    global _tts
    if _tts is not None:
        return _tts
    import sherpa_onnx
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=str(_BUNDLE / "model.onnx"),
                voices=str(_BUNDLE / "voices.bin"),
                tokens=str(_BUNDLE / "tokens.txt"),
                data_dir=str(_BUNDLE / "espeak-ng-data"),
                lexicon=str(_BUNDLE / "lexicon-us-en.txt"),
            ),
            num_threads=4,
        ),
    )
    _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts


def synth(text: str, voice: str, seed: int | None = None, speed: float = 1.0):
    """Synthesize text. `voice` is a Kokoro speaker ID as string, e.g. "21"."""
    try:
        sid = int(voice)
    except ValueError:
        raise ValueError(f"Kokoro voice must be integer SID, got {voice!r}")
    tts = _load()
    # sherpa-onnx OfflineTts.generate — seed isn't exposed; we get determinism
    # from the model weights. Variants come from varying speed/etc.
    audio = tts.generate(text=text, sid=sid, speed=speed)
    x = np.asarray(audio.samples, dtype=np.float32)
    return x, audio.sample_rate


def speaker_name(voice: str) -> str:
    """Human-readable name for a Kokoro speaker ID."""
    names = {
        0:"af_alloy",1:"af_aoede",2:"af_bella",3:"af_heart",4:"af_jessica",
        5:"af_kore",6:"af_nicole",7:"af_nova",8:"af_river",9:"af_sarah",10:"af_sky",
        11:"am_adam",12:"am_echo",13:"am_eric",14:"am_fenrir",15:"am_liam",
        16:"am_michael",17:"am_onyx",18:"am_puck",19:"am_santa",
        20:"bf_alice",21:"bf_emma",22:"bf_isabella",23:"bf_lily",
        24:"bm_daniel",25:"bm_fable",26:"bm_george",27:"bm_lewis",
    }
    try: sid = int(voice)
    except ValueError: return voice
    return names.get(sid, f"sid{sid}")
