using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;

namespace VGTTS.Prerender;

/// <summary>
/// First-stage audio resolution. Checks if a line was pre-rendered at build time
/// and returns the OGG file path, or null on miss (caller falls through to live
/// TTS). Manifest is loaded once on Awake; lookups are O(1) on a SHA-256 hex key.
///
/// Bundle layout (relative to plugin DLL):
///   VGTTS/prerender/manifest.json
///   VGTTS/prerender/&lt;sha256&gt;.ogg       ← one per pre-rendered line
/// </summary>
internal sealed class PrerenderLookup
{
    private readonly Dictionary<string, string> _keyToPath;
    private readonly string _packDir;
    public int EntryCount => _keyToPath.Count;

    public PrerenderLookup()
    {
        _keyToPath = new Dictionary<string, string>();
        var pluginDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        _packDir = Path.Combine(pluginDir, "VGTTS", "prerender");
        LoadManifest();
    }

    private void LoadManifest()
    {
        var manifestPath = Path.Combine(_packDir, "manifest.json");
        if (!File.Exists(manifestPath)) return;
        try
        {
            var json = File.ReadAllText(manifestPath);
            var parsed = JsonConvert.DeserializeObject<Dictionary<string, ManifestEntry>>(json);
            if (parsed == null) return;
            foreach (var kv in parsed)
            {
                var ogg = Path.Combine(_packDir, kv.Value.Ogg ?? (kv.Key + ".ogg"));
                if (File.Exists(ogg))
                    _keyToPath[kv.Key] = ogg;
            }
        }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"Failed to load prerender manifest: {ex.Message}");
        }
    }

    /// <summary>Return the OGG path for (text, speaker), or null if not in the pack.</summary>
    public string? Resolve(string normalizedText, string speakerName)
    {
        var key = ComputeKey(normalizedText, speakerName);
        return _keyToPath.TryGetValue(key, out var path) ? path : null;
    }

    /// <summary>Hash the exact same way the Python renderer does: sha256(utf8(text) + 0x00 + utf8(speaker)).</summary>
    internal static string ComputeKey(string normalizedText, string speakerName)
    {
        using var sha = SHA256.Create();
        var a = Encoding.UTF8.GetBytes(normalizedText ?? "");
        var b = Encoding.UTF8.GetBytes(speakerName ?? "");
        var buf = new byte[a.Length + 1 + b.Length];
        Buffer.BlockCopy(a, 0, buf, 0, a.Length);
        buf[a.Length] = 0;
        Buffer.BlockCopy(b, 0, buf, a.Length + 1, b.Length);
        var hash = sha.ComputeHash(buf);
        var hex = new StringBuilder(hash.Length * 2);
        foreach (var bb in hash) hex.Append(bb.ToString("x2"));
        return hex.ToString();
    }

    [JsonObject(MemberSerialization.OptIn)]
    private sealed class ManifestEntry
    {
        [JsonProperty("ogg")] public string? Ogg { get; set; }
    }
}
