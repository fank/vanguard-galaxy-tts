using System;
using System.Collections.Generic;
using System.IO;
using BepInEx;

namespace VGTTS.Prerender;

/// <summary>
/// Records every dialogue line that arrives without a pre-rendered OGG.
/// Writes a TSV at <c>BepInEx/cache/VGTTS/unprerendered.tsv</c> with one row
/// per unique (speaker, text). Users harvest this file between patches to
/// drive the next render delta — see <c>tools/prerender/render_missing.py</c>.
///
/// Deduplication is session-scoped in memory AND persisted across sessions —
/// the file is loaded on startup, existing entries skipped so the log never
/// grows unbounded. Each row is:
///
///   isoTimestamp \t speaker \t normalizedText \t sha256key
///
/// Thread-safety: a single instance, synchronized on <c>_lock</c>. Dialogue
/// playback is Unity-main-thread so contention is rare but we guard anyway.
/// </summary>
internal sealed class UnprerenderedLog
{
    private readonly string _path;
    private readonly HashSet<string> _seenKeys = new();
    private readonly object _lock = new();

    public int SeenCount { get { lock (_lock) return _seenKeys.Count; } }

    public UnprerenderedLog(string fileName = "unprerendered.tsv")
    {
        var dir = Path.Combine(Paths.CachePath, "VGTTS");
        Directory.CreateDirectory(dir);
        _path = Path.Combine(dir, fileName);
        LoadExisting();
    }

    private void LoadExisting()
    {
        if (!File.Exists(_path)) return;
        try
        {
            foreach (var line in File.ReadAllLines(_path))
            {
                if (string.IsNullOrWhiteSpace(line) || line.StartsWith("#")) continue;
                var parts = line.Split('\t');
                if (parts.Length >= 4) _seenKeys.Add(parts[3]);
            }
            Plugin.Log.LogInfo($"Loaded {_seenKeys.Count} previously-seen unprerendered lines from {_path}");
        }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"Failed to load unprerendered log: {ex.Message}");
        }
    }

    /// <summary>Record a miss; returns true on first sight this session.</summary>
    public bool Record(string speaker, string normalizedText, string key)
    {
        lock (_lock)
        {
            if (!_seenKeys.Add(key)) return false;
            try
            {
                if (!File.Exists(_path))
                {
                    File.WriteAllText(_path,
                        "# vgtts unprerendered-lines log. Format: timestamp<TAB>speaker<TAB>normalized_text<TAB>sha256key\n" +
                        "# Harvest this file with tools/prerender/render_missing.py to render deltas.\n");
                }
                var row = $"{DateTime.UtcNow:yyyy-MM-ddTHH:mm:ssZ}\t{Escape(speaker)}\t{Escape(normalizedText)}\t{key}\n";
                File.AppendAllText(_path, row);
            }
            catch (Exception ex)
            {
                Plugin.Log.LogWarning($"Failed to write unprerendered log row: {ex.Message}");
            }
            return true;
        }
    }

    private static string Escape(string s) =>
        (s ?? "").Replace("\\", "\\\\").Replace("\t", "\\t").Replace("\n", "\\n").Replace("\r", "\\r");
}
