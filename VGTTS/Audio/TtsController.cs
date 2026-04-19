using System.Collections;
using System.Threading;
using System.Threading.Tasks;
using Behaviour.AudioSystem;
using Behaviour.Util;
using Source.AudioSystem;
using UnityEngine;
using VGTTS.Cache;
using VGTTS.Prerender;
using VGTTS.Text;
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
    private readonly PrerenderLookup _prerender;
    private readonly UnprerenderedLog _unprerendered;
    private CancellationTokenSource? _currentCts;
    private SoundEmitter? _currentEmitter;
    private GameObject? _fallbackGo;

    public TtsController(ITtsProvider provider, DiskCache cache, VoiceMapper voices,
                         PrerenderLookup prerender, UnprerenderedLog unprerendered)
    {
        _provider = provider;
        _cache = cache;
        _voices = voices;
        _prerender = prerender;
        _unprerendered = unprerendered;
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
    /// Ensure the disk cache holds a synth of (text, voice-for-speaker) without
    /// playing anything. Used by <see cref="CaptainNameCache"/> to pre-warm
    /// name-substituted dialogue lines on a background task so the first
    /// utterance in dialogue doesn't pay a synth penalty.
    /// </summary>
    public async Task<WarmResult> WarmCacheAsync(string speaker, string text, CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(text)) return WarmResult.Skipped;
        var synthText = TextNormalizer.ForTts(text);
        var voice = _voices.Resolve(speaker);
        var path = _cache.PathFor(synthText, voice);
        if (_cache.Exists(path)) return WarmResult.AlreadyCached;
        await _provider.SynthesizeAsync(synthText, voice, path, ct).ConfigureAwait(false);
        return WarmResult.Synthesized;
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
        var synthText = TextNormalizer.ForTts(text);

        // 1. Prerender path — premium baked audio, voice already chosen at build time.
        var prerenderedPath = _prerender.Resolve(synthText, speaker);
        if (prerenderedPath != null)
        {
            AudioClip? prerenderedClip = null;
            yield return AudioClipLoader.LoadOgg(prerenderedPath, c => prerenderedClip = c);
            if (prerenderedClip != null && !ct.IsCancellationRequested)
            {
                PlayClip(prerenderedClip);
                yield break;
            }
        }
        else
        {
            // Miss — log once per (speaker, text) so users can see at a glance which lines
            // fell through to live TTS and harvest them for the next render pass.
            var key = PrerenderLookup.ComputeKey(synthText, speaker);
            if (_unprerendered.Record(speaker, synthText, key))
            {
                Plugin.Log.LogWarning(
                    $"[prerender-miss] {speaker}: \"{synthText}\" — falling back to live TTS. " +
                    $"Harvest BepInEx/cache/VGTTS/unprerendered.tsv for the next render pass.");
            }
        }

        // 2. Live fallback — Kokoro (or configured provider) with per-character voice mapping.
        var voice = _voices.Resolve(speaker);
        var path = _cache.PathFor(synthText, voice);

        if (!_cache.Exists(path))
        {
            var task = _provider.SynthesizeAsync(synthText, voice, path, ct);
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
