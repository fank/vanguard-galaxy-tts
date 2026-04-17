using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace VGTTS.TTS;

/// <summary>
/// Zero-dependency Windows TTS via PowerShell shelling out to
/// <c>System.Speech.Synthesis.SpeechSynthesizer</c>. Uses <c>-EncodedCommand</c> to
/// sidestep shell escaping. Slow (~1 s cold start per call) but ships with Windows.
/// </summary>
internal sealed class SapiProvider : ITtsProvider
{
    public string Name => "sapi";

    public Task<string> SynthesizeAsync(string text, string voice, string outputPath, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

            var script = BuildScript(text, voice, outputPath);
            var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));

            var psi = new ProcessStartInfo("powershell.exe",
                $"-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand {encoded}")
            {
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
            };

            using var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Failed to start powershell.exe");

            using var ctReg = ct.Register(() => { try { proc.Kill(); } catch { } });
            proc.WaitForExit();

            if (proc.ExitCode != 0 || !File.Exists(outputPath) || new FileInfo(outputPath).Length == 0)
            {
                var err = proc.StandardError.ReadToEnd();
                throw new InvalidOperationException(
                    $"SAPI synthesis failed (exit {proc.ExitCode}): {err.Trim()}");
            }

            return outputPath;
        }, ct);
    }

    private static string BuildScript(string text, string voice, string outputPath)
    {
        var sb = new StringBuilder();
        sb.AppendLine("Add-Type -AssemblyName System.Speech");
        sb.AppendLine("$s = New-Object System.Speech.Synthesis.SpeechSynthesizer");
        if (!string.IsNullOrEmpty(voice))
            sb.AppendLine($"try {{ $s.SelectVoice('{PsEscape(voice)}') }} catch {{ }}");
        sb.AppendLine($"$s.SetOutputToWaveFile('{PsEscape(outputPath)}')");
        sb.AppendLine($"$s.Speak('{PsEscape(text)}')");
        sb.AppendLine("$s.Dispose()");
        return sb.ToString();
    }

    // PowerShell single-quoted strings: only ' needs to be escaped by doubling.
    private static string PsEscape(string s) => s.Replace("'", "''");
}
