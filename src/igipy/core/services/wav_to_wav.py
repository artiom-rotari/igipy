import wave
from io import BytesIO
from pathlib import Path

from igipy.core.formats.wav import WAV


def wav_to_wav(source_io: BytesIO, source_path: Path | None = None) -> tuple[BytesIO, Path | None]:
    target_path: Path | None = source_path.with_suffix(".wav") if source_path is not None else None
    wav_instance = WAV.model_validate_stream(source_io)
    target_io = BytesIO()

    with wave.open(target_io, mode="w") as wave_stream:
        wave_stream.setnchannels(wav_instance.header.channels)
        wave_stream.setsampwidth(wav_instance.header.sample_width // 8)
        wave_stream.setframerate(wav_instance.header.framerate)
        wave_stream.writeframesraw(wav_instance.samples)

    return target_io, target_path
