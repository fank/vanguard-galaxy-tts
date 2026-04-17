using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace VGTTS.TTS;

/// <summary>
/// Offline neural TTS via Piper (ONNX). Spawns <c>piper.exe</c> per synthesis,
/// feeds text on stdin, reads the resulting WAV path back. Expects the bundle at:
/// <c>&lt;plugins&gt;/VGTTS/tools/piper/piper.exe</c> and voice models under
/// <c>&lt;plugins&gt;/VGTTS/tools/voices/&lt;voiceId&gt;.onnx</c>.
/// </summary>
internal sealed class PiperProvider : ITtsProvider
{
    public string Name => "piper";

    private readonly string _piperExe;
    private readonly string _voicesDir;
    private readonly string _defaultVoice;

    public PiperProvider(string defaultVoice)
    {
        _defaultVoice = defaultVoice;

        var pluginDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        var bundleDir = Path.Combine(pluginDir, "VGTTS", "tools");
        _piperExe = Path.Combine(bundleDir, "piper", "piper.exe");
        _voicesDir = Path.Combine(bundleDir, "voices");

        if (!File.Exists(_piperExe))
            throw new FileNotFoundException($"piper.exe not found at {_piperExe}. Run 'make deploy' to install bundle.");
    }

    public Task<string> SynthesizeAsync(string text, string voice, string outputPath, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            var voiceId = string.IsNullOrWhiteSpace(voice) ? _defaultVoice : voice;
            var modelPath = Path.Combine(_voicesDir, voiceId + ".onnx");
            if (!File.Exists(modelPath))
                throw new FileNotFoundException($"Piper voice model not found: {modelPath}");

            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

            var psi = new ProcessStartInfo(_piperExe)
            {
                Arguments = $"--model \"{modelPath}\" --output_file \"{outputPath}\"",
                WorkingDirectory = Path.GetDirectoryName(_piperExe),
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                StandardInputEncoding = Encoding.UTF8,
            };

            using var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Failed to start piper.exe");

            using var ctReg = ct.Register(() => { try { proc.Kill(); } catch { } });

            proc.StandardInput.Write(text);
            proc.StandardInput.Close();
            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit();

            if (proc.ExitCode != 0 || !File.Exists(outputPath) || new FileInfo(outputPath).Length == 0)
                throw new InvalidOperationException(
                    $"Piper synthesis failed (exit {proc.ExitCode}): {stderr.Trim()}");

            return outputPath;
        }, ct);
    }
}
