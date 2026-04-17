using System.Collections;
using System.Threading;
using Behaviour.AudioSystem;
using Behaviour.Util;
using Source.AudioSystem;
using UnityEngine;
using VGTTS.Cache;
using VGTTS.TTS;
using VGTTS.Voice;

namespace VGTTS.Audio;

/// <summary>
/// Orchestrates the full pipeline: cache lookup → (synth if miss) → load clip → play.
/// Serializes one line at a time; a new <see cref="Speak"/> cancels whatever is in flight.
/// </summary>
internal sealed class TtsController
{
    public static TtsController? Instance { get; set; }

    private readonly ITtsProvider _provider;
    private readonly DiskCache _cache;
    private readonly VoiceMapper _voices;
    private CancellationTokenSource? _currentCts;
    private SoundEmitter? _currentEmitter;
    private GameObject? _fallbackGo;

    public TtsController(ITtsProvider provider, DiskCache cache, VoiceMapper voices)
    {
        _provider = provider;
        _cache = cache;
        _voices = voices;
    }

    public void Speak(string speaker, string text)
    {
        if (string.IsNullOrWhiteSpace(text) || Plugin.Instance == null) return;

        Stop();

        var cts = new CancellationTokenSource();
        _currentCts = cts;
        Plugin.Instance.StartCoroutine(SpeakCoroutine(speaker, text, cts.Token));
    }

    /// <summary>
    /// Interrupt any in-flight synthesis and fade out any currently playing audio.
    /// Called on dialogue advance, dialogue close, and ECHO tip dismiss.
    /// </summary>
    public void Stop()
    {
        _currentCts?.Cancel();
        _currentCts = null;
        StopCurrent();
    }

    private IEnumerator SpeakCoroutine(string speaker, string text, CancellationToken ct)
    {
        var voice = _voices.Resolve(speaker);
        var path = _cache.PathFor(text, voice);

        if (!_cache.Exists(path))
        {
            var task = _provider.SynthesizeAsync(text, voice, path, ct);
            while (!task.IsCompleted)
            {
                if (ct.IsCancellationRequested) yield break;
                yield return null;
            }
            if (task.IsFaulted)
            {
                Plugin.Log.LogError($"[tts] {_provider.Name} synth failed: {task.Exception?.GetBaseException().Message}");
                yield break;
            }
        }

        if (ct.IsCancellationRequested) yield break;

        AudioClip? clip = null;
        yield return AudioClipLoader.LoadWav(path, c => clip = c);
        if (clip == null || ct.IsCancellationRequested) yield break;

        PlayClip(clip);
    }

    private void PlayClip(AudioClip clip)
    {
        StopCurrent();

        var mgr = PersistentSingleton<SoundManager>.Instance;
        if (mgr != null)
        {
            var soundData = new SoundData
            {
                clip = clip,
                volume = 1.0f,
                loop = false,
                playOnAwake = false,
                minPitch = 1.0f,
                maxPitch = 1.0f,
                frequentSound = false,
            };
            _currentEmitter = mgr.CreateSound().WithSoundData(soundData).PlayReturn();
            return;
        }

        // Fallback: plain AudioSource on a detached GameObject.
        _fallbackGo = new GameObject("VGTTS_Playback");
        Object.DontDestroyOnLoad(_fallbackGo);
        var src = _fallbackGo.AddComponent<AudioSource>();
        src.clip = clip;
        src.volume = 1.0f;
        src.Play();
        Object.Destroy(_fallbackGo, clip.length + 0.5f);
    }

    private void StopCurrent()
    {
        if (_currentEmitter != null)
        {
            try { _currentEmitter.Stop(); } catch { /* emitter may already be returning to pool */ }
            _currentEmitter = null;
        }

        if (_fallbackGo != null)
        {
            Object.Destroy(_fallbackGo);
            _fallbackGo = null;
        }
    }
}
