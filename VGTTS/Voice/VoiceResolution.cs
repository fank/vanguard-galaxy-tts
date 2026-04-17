namespace VGTTS.Voice;

/// <summary>
/// A character's resolved voice profile. <see cref="Voice"/> is the opaque
/// provider-specific string (Piper accepts <c>model</c> or <c>model/speaker</c>);
/// <see cref="Pitch"/> is applied at the Unity AudioSource level so tweaks don't
/// invalidate cached WAVs.
/// </summary>
internal readonly struct VoiceResolution
{
    public string Voice { get; }
    public float Pitch { get; }

    public VoiceResolution(string voice, float pitch)
    {
        Voice = voice;
        Pitch = pitch;
    }
}
