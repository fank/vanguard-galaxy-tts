using System.Threading;
using System.Threading.Tasks;

namespace VGTTS.TTS;

/// <summary>
/// Dispatches each request to the right provider based on the voice string.
/// Voices prefixed with <c>kokoro:</c> go to Kokoro (if available);
/// everything else goes to the primary provider (Piper/SAPI). Enables
/// per-character provider selection — you can point ECHO at Kokoro for
/// better prosody while the rest of the roster stays on Piper.
/// </summary>
internal sealed class ProviderRouter : ITtsProvider
{
    private readonly ITtsProvider _primary;
    private readonly ITtsProvider? _kokoro;

    public ProviderRouter(ITtsProvider primary, ITtsProvider? kokoro)
    {
        _primary = primary;
        _kokoro = kokoro;
    }

    public string Name => _kokoro != null ? $"{_primary.Name}+kokoro" : _primary.Name;

    public Task<string> SynthesizeAsync(string text, string voice, string outputPath, CancellationToken ct)
    {
        if (KokoroProvider.IsKokoroVoice(voice) && _kokoro != null)
            return _kokoro.SynthesizeAsync(text, voice, outputPath, ct);
        return _primary.SynthesizeAsync(text, voice, outputPath, ct);
    }
}
