using System.Collections.Generic;
using BepInEx.Configuration;

namespace VGTTS.Voice;

/// <summary>
/// Maps <c>Character.name</c> → <see cref="VoiceResolution"/> (voice string +
/// playback pitch) via three BepInEx config sections:
///   <c>[Voices]</c> — <c>CharacterName = model</c> or <c>model/speakerId</c>
///   <c>[Pitch]</c>  — <c>CharacterName = 1.0</c> (range ~0.85–1.15)
/// Pre-seeds well-known NPCs with hand-picked voice+pitch combos so each named
/// character sounds distinct out of the box; unseen characters auto-bind to the
/// global default on first encounter.
/// </summary>
internal sealed class VoiceMapper
{
    private const string VoiceSection = "Voices";
    private const string PitchSection = "Pitch";

    private readonly ConfigFile _config;
    private readonly string _defaultVoice;
    private readonly IReadOnlyDictionary<string, (string Voice, float Pitch)> _seeds;
    private readonly Dictionary<string, (ConfigEntry<string> Voice, ConfigEntry<float> Pitch)> _cache = new();

    public VoiceMapper(ConfigFile config, string defaultVoice,
        IReadOnlyDictionary<string, (string Voice, float Pitch)> seeds)
    {
        _config = config;
        _defaultVoice = defaultVoice;
        _seeds = seeds;

        // Pre-bind every seed so the config file presents the full known NPC
        // list on first launch, ready to tweak.
        foreach (var name in seeds.Keys) Bind(name);
    }

    public VoiceResolution Resolve(string speaker)
    {
        if (string.IsNullOrWhiteSpace(speaker))
            return new VoiceResolution(_defaultVoice, 1.0f);
        var (voiceEntry, pitchEntry) = Bind(speaker);
        return new VoiceResolution(voiceEntry.Value, pitchEntry.Value);
    }

    private (ConfigEntry<string> Voice, ConfigEntry<float> Pitch) Bind(string speaker)
    {
        if (_cache.TryGetValue(speaker, out var cached)) return cached;

        var (seedVoice, seedPitch) = _seeds.TryGetValue(speaker, out var s)
            ? s
            : (_defaultVoice, 1.0f);

        var voiceEntry = _config.Bind(VoiceSection, speaker, seedVoice,
            $"Voice for '{speaker}'. Format: 'model' or 'model/speakerId' (for multi-speaker " +
            $"models like en_US-libritts_r-medium, speakerId in 0-903). Drop any *.onnx into " +
            $"plugins/VGTTS/tools/voices/ and use the filename without extension here.");

        var pitchEntry = _config.Bind(PitchSection, speaker, seedPitch,
            $"Playback pitch for '{speaker}'. 1.0 = default, range ~0.85-1.15 sounds natural. " +
            $"Applied at Unity AudioSource level — changing it does NOT invalidate the TTS cache.");

        var tuple = (voiceEntry, pitchEntry);
        _cache[speaker] = tuple;
        return tuple;
    }
}
