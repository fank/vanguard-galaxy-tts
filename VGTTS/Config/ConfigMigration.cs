using System;
using System.IO;
using BepInEx.Configuration;

namespace VGTTS.Config;

/// <summary>
/// One-shot config file cleanup for users updating from an older mod version.
///
/// BepInEx's <see cref="ConfigFile"/> is sticky: once a value is on disk it's
/// never updated even when the code's default changes. That means NPC voice
/// choices from v1.1 survive a v1.2 install, producing subtle bugs — Arle
/// heard as male, Elias as female, 27 other NPCs slightly off from the new
/// Kokoro-direct defaults.
///
/// This class runs <i>before</i> any <see cref="ConfigFile.Bind{T}"/> call.
/// It reads the raw .cfg file, checks for hallmarks of an older schema
/// (a <c>[Pitch]</c> section — v1.2 removed pitch entirely), and if found,
/// strips the stale <c>[Pitch]</c> and <c>[Voices]</c> sections so the
/// plugin's <c>Config.Bind</c> calls re-populate them from current defaults.
///
/// Backup is written to <c>&lt;cfg&gt;.v1.bak</c> before any edit.
/// </summary>
internal static class ConfigMigration
{
    private const int CurrentSchemaVersion = 2;

    public static void MigrateIfNeeded(ConfigFile config)
    {
        var path = config.ConfigFilePath;
        if (!File.Exists(path)) return; // Fresh install — nothing to migrate.

        string contents;
        try { contents = File.ReadAllText(path); }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"[config-migration] Couldn't read {path}: {ex.Message}");
            return;
        }

        // v1 hallmark: [Pitch] section exists (v1.2 removed pitch entirely).
        var hasPitch = contents.Contains("[Pitch]");
        if (!hasPitch) return; // Already v2 schema, or never had Pitch.

        try
        {
            var backup = path + ".v1.bak";
            File.WriteAllText(backup, contents);
            Plugin.Log.LogInfo($"[config-migration] Backed up v1 config to {Path.GetFileName(backup)}");

            var cleaned = StripSections(contents, "Pitch", "Voices");
            File.WriteAllText(path, cleaned);
            Plugin.Log.LogInfo(
                $"[config-migration] Stripped stale [Pitch] + [Voices] sections from {Path.GetFileName(path)}. " +
                $"They will be rebuilt from current defaults on the next Bind() call.");

            // BepInEx already parsed the file once at construction; reload so the in-memory
            // state matches our on-disk edits before Config.Bind() runs.
            config.Reload();
        }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"[config-migration] Migration failed: {ex.Message}. Plugin will still run.");
        }
    }

    /// <summary>Remove entire [Section] blocks (header, descriptions, entries) from a
    /// BepInEx .cfg file. Section blocks run from their [Header] line until the next
    /// [Header] or EOF.</summary>
    private static string StripSections(string cfg, params string[] sectionNames)
    {
        var lines = cfg.Replace("\r\n", "\n").Split('\n');
        var output = new System.Text.StringBuilder(cfg.Length);
        var skipping = false;
        foreach (var line in lines)
        {
            if (line.StartsWith("[") && line.Contains("]"))
            {
                // New section header — decide whether to skip.
                var header = line.Trim('[', ']', ' ');
                skipping = Array.Exists(sectionNames,
                    n => string.Equals(n, header, StringComparison.OrdinalIgnoreCase));
            }
            if (!skipping) output.AppendLine(line);
        }
        return output.ToString();
    }
}
