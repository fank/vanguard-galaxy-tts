using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace VGTTS.Prerender;

public enum WarmResult { AlreadyCached, Synthesized, Skipped }

/// <summary>
/// Pre-warms the disk cache with name-substituted captain.name dialogue lines.
///
/// ~17 story lines like <c>"Captain " + captain.name + ", you took your time..."</c>
/// can't be prerendered at build time (the player's callsign is unknown).
/// Without this warm-up the first utterance of each line pays a ~0.5-1s
/// synthesis penalty on the dialogue hot path.
///
/// Templates ship as <c>VGTTS/prerender/captain_name_templates.json</c>. On
/// <c>Characters.CreateCaptain</c> postfix, <see cref="WarmInBackground"/>
/// substitutes <c>{captain}</c> with the commander's callsign and synthesizes
/// each line via the TTS provider (background task, fire-and-forget).
/// Dialogue playback then hits the cache with zero synth lag.
/// </summary>
internal static class CaptainNameCache
{
    private const string CaptainPlaceholder = "{captain}";
    private static string? _lastWarmedName;
    private static readonly HashSet<(string Speaker, string Text)> _warmedLines = new();
    private static readonly object _warmedLock = new();

    public static void WarmInBackground(string commanderName)
    {
        if (string.IsNullOrEmpty(commanderName)) return;
        if (_lastWarmedName == commanderName) return;
        _lastWarmedName = commanderName;

        _ = Task.Run(() => WarmAsync(commanderName, CancellationToken.None));
    }

    /// <summary>Returns true if (speaker, text) is a captain-name substitution line
    /// that was warmed into the DiskCache at game start. Used by TtsController to
    /// downgrade the misleading <c>[prerender-miss]</c> warning to INFO for these
    /// lines — they miss the manifest by design but play from warm cache without
    /// synthesis lag.</summary>
    public static bool IsWarmedLine(string speaker, string text)
    {
        lock (_warmedLock) return _warmedLines.Contains((speaker, text));
    }

    private static async Task WarmAsync(string commanderName, CancellationToken ct)
    {
        var templates = LoadTemplates();
        if (templates.Count == 0) return;

        var controller = Audio.TtsController.Instance;
        if (controller == null) return;

        Plugin.Log.LogInfo($"[captain-warm] Warming {templates.Count} captain.name lines for '{commanderName}'");
        int warmed = 0, cached = 0, failed = 0;
        lock (_warmedLock) _warmedLines.Clear();
        foreach (var t in templates)
        {
            if (ct.IsCancellationRequested) break;
            var text = t.Template.Replace(CaptainPlaceholder, commanderName);
            try
            {
                var result = await controller.WarmCacheAsync(t.Speaker, text, ct).ConfigureAwait(false);
                if (result == WarmResult.Synthesized) warmed++;
                else if (result == WarmResult.AlreadyCached) cached++;
                lock (_warmedLock) _warmedLines.Add((t.Speaker, text));
            }
            catch (Exception ex)
            {
                failed++;
                Plugin.Log.LogWarning($"[captain-warm] {t.Speaker}: {ex.Message}");
            }
        }
        Plugin.Log.LogInfo($"[captain-warm] Done. synthesized={warmed} already-cached={cached} failed={failed}");
    }

    private static List<CaptainNameTemplate> LoadTemplates()
    {
        var pluginDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        var path = Path.Combine(pluginDir, "prerender", "captain_name_templates.json");
        if (!File.Exists(path))
        {
            Plugin.Log.LogWarning($"[captain-warm] Templates not found at {path}; skipping warm-up.");
            return new List<CaptainNameTemplate>();
        }
        try
        {
            var json = File.ReadAllText(path);
            return JsonConvert.DeserializeObject<List<CaptainNameTemplate>>(json)
                   ?? new List<CaptainNameTemplate>();
        }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"[captain-warm] Failed to load templates: {ex.Message}");
            return new List<CaptainNameTemplate>();
        }
    }

    [JsonObject(MemberSerialization.OptIn)]
    private sealed class CaptainNameTemplate
    {
        [JsonProperty("speaker")] public string Speaker { get; set; } = "";
        [JsonProperty("template")] public string Template { get; set; } = "";
    }
}
