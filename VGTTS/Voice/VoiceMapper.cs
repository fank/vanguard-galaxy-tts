using System.Collections.Generic;
using BepInEx.Configuration;

namespace VGTTS.Voice;

/// <summary>
/// Maps <c>Character.name</c> → voice string via the <c>[Voices]</c> config
/// section. Pre-seeds well-known NPCs with hand-picked <c>kokoro:SID</c> values
/// so each named character sounds distinct out of the box; unseen characters
/// auto-bind to the global default on first encounter.
/// </summary>
internal sealed class VoiceMapper
{
    private const string VoiceSection = "Voices";

    private readonly ConfigFile _config;
    private readonly string _defaultVoice;
    private readonly IReadOnlyDictionary<string, string> _seeds;
    private readonly Dictionary<string, ConfigEntry<string>> _cache = new();

    public VoiceMapper(ConfigFile config, string defaultVoice,
        IReadOnlyDictionary<string, string> seeds)
    {
        _config = config;
        _defaultVoice = defaultVoice;
        _seeds = seeds;

        // Pre-bind every seed so the config file presents the full known NPC
        // list on first launch, ready to tweak.
        foreach (var name in seeds.Keys) Bind(name);
    }

    public string Resolve(string speaker)
    {
        if (string.IsNullOrWhiteSpace(speaker)) return _defaultVoice;
        return Bind(speaker).Value;
    }

    private ConfigEntry<string> Bind(string speaker)
    {
        if (_cache.TryGetValue(speaker, out var cached)) return cached;

        var seed = _seeds.TryGetValue(speaker, out var s) ? s : _defaultVoice;
        var entry = _config.Bind(VoiceSection, speaker, seed,
            $"Voice for '{speaker}'. Format: 'model' or 'model/speakerId' (for multi-speaker " +
            $"models like en_US-libritts_r-medium, speakerId in 0-903). Drop any *.onnx into " +
            $"plugins/VGTTS/tools/voices/ and use the filename without extension here.");
        _cache[speaker] = entry;
        return entry;
    }
}
