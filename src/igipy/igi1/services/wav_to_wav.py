import wave
from io import BytesIO

from igipy.core.formats.wav import WAV


def wav_to_wav(instance: WAV) -> tuple[BytesIO, str]:
    """Convert an IGI WAV (possibly ADPCM-encoded) to a standard WAV file."""
    stream = BytesIO()
    samples = instance.samples

    with wave.open(stream, "w") as wave_stream:
        wave_stream.setnchannels(instance.header.channels)
        wave_stream.setsampwidth(instance.header.sample_width // 8)
        wave_stream.setframerate(instance.header.framerate)
        wave_stream.writeframesraw(samples)

    return stream, ".wav"
