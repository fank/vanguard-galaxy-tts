using System.Collections.Generic;
using BepInEx.Configuration;

namespace VGTTS.Voice;

/// <summary>
/// Maps <c>Character.name</c> → provider-specific voice id via the BepInEx
/// <see cref="ConfigFile"/>. Pre-seeds well-known NPCs from
/// <see cref="DefaultVoiceMap"/>; every other speaker auto-binds with the global
/// default on first encounter (so unknown characters populate the config over time).
/// </summary>
internal sealed class VoiceMapper
{
    private const string Section = "Voices";

    private readonly ConfigFile _config;
    private readonly string _defaultVoice;
    private readonly IReadOnlyDictionary<string, string> _seeds;
    private readonly Dictionary<string, ConfigEntry<string>> _cache = new();

    public VoiceMapper(ConfigFile config, string defaultVoice, IReadOnlyDictionary<string, string> seeds)
    {
        _config = config;
        _defaultVoice = defaultVoice;
        _seeds = seeds;

        // Pre-bind all seeds up-front so the config file contains the full known list
        // on first launch, ready to edit.
        foreach (var name in seeds.Keys)
            Bind(name);
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
        var entry = _config.Bind(Section, speaker, seed,
            $"Voice id for '{speaker}'. Bundled: en_US-amy-medium, en_US-ryan-medium, en_GB-alan-medium. " +
            $"Drop any *.onnx into plugins/VGTTS/tools/voices/ and use the filename without extension here.");
        _cache[speaker] = entry;
        return entry;
    }
}
