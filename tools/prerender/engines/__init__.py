"""TTS backends. Each exposes `synth(text, voice, **opts) -> (samples, sample_rate)`
where samples is a float32 numpy array in [-1, 1]."""
