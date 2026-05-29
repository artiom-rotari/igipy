import struct

# Standard IMA ADPCM step-size table (89 entries)
step_size_table = [
    *[7, 8, 9, 10, 11, 12, 13, 14, 16, 17],
    *[19, 21, 23, 25, 28, 31, 34, 37, 41, 45],
    *[50, 55, 60, 66, 73, 80, 88, 97, 107, 118],
    *[130, 143, 157, 173, 190, 209, 230, 253, 279, 307],
    *[337, 371, 408, 449, 494, 544, 598, 658, 724, 796],
    *[876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066],
    *[2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358],
    *[5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899],
    *[15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767],
]

# Standard IMA ADPCM index adjustment table
index_table = [
    *[-1, -1, -1, -1, 2, 4, 6, 8],
    *[-1, -1, -1, -1, 2, 4, 6, 8],
]


def encode(data: bytes, channels: int = 1) -> bytes:  # noqa: PLR0915, PLR0912, C901
    """
    Encodes raw 16-bit PCM audio into a custom 4-bit ADPCM format,
    with support for multiple interleaved channels.

    :param data: A byte string of raw, interleaved 16-bit PCM samples.
    :param channels: The number of audio channels (e.g., 1 for mono, 2 for stereo).
    :return: The compressed byte string.
    """
    # Standard IMA ADPCM tables

    if not data or channels < 1:
        return b""

    # The total number of samples across all channels
    num_samples = len(data) // 2
    try:
        samples = struct.unpack(f"<{num_samples}h", data)
    except struct.error:
        return b""

    # --- Multi-channel state initialization ---
    states = [{"predictor": 0, "step_index": 0} for _ in range(channels)]

    nibbles = []

    # Process each sample, applying the state for its respective channel
    for i, sample in enumerate(samples):
        # Determine which channel this sample belongs to
        channel_idx = i % channels

        # Get the current state for this channel
        state = states[channel_idx]
        predictor = state["predictor"]
        step_index = state["step_index"]

        step = step_size_table[step_index]
        diff = sample - predictor

        # Quantize the difference into a 4-bit code
        code = 0
        if diff < 0:
            code = 8
            diff = -diff

        if diff >= step:
            code |= 4
            diff -= step
        if diff >= step >> 1:
            code |= 2
            diff -= step >> 1
        if diff >= step >> 2:
            code |= 1
            diff -= step >> 2

        nibbles.append(code)

        # Update the predictor based on the reconstructed difference
        reconstructed_diff = step >> 3
        if code & 1:
            reconstructed_diff += step >> 2
        if code & 2:
            reconstructed_diff += step >> 1
        if code & 4:
            reconstructed_diff += step

        if code & 8:
            predictor -= reconstructed_diff
        else:
            predictor += reconstructed_diff

        # Clamp predictor to 16-bit range
        if predictor > 32767:  # noqa: PLR2004
            predictor = 32767
        elif predictor < -32768:  # noqa: PLR2004
            predictor = -32768

        # Adapt the step size for the next sample
        step_index += index_table[code & 7]
        if step_index < 0:
            step_index = 0
        elif step_index > 88:  # noqa: PLR2004
            step_index = 88

        # --- Store the updated state for the current channel ---
        state["predictor"] = predictor
        state["step_index"] = step_index

    # Pack the 4-bit nibbles into bytes
    output_bytes = bytearray()
    for i in range(0, len(nibbles), 2):
        nibble1 = nibbles[i]
        if i + 1 < len(nibbles):  # noqa: SIM108
            nibble2 = nibbles[i + 1]
        else:
            nibble2 = 0  # Pad with a 0 nibble for an odd total sample count

        output_bytes.append((nibble1 << 4) | nibble2)

    # Append the terminator byte for an even total sample count
    if num_samples > 0 and num_samples % 2 == 0:
        output_bytes.append(0xAB)

    return bytes(output_bytes)


def decode(data: bytes, channels: int = 1) -> bytes:  # noqa: PLR0912, C901
    """
    Decodes data from a custom 4-bit ADPCM format back into raw 16-bit PCM audio,
    with support for multiple interleaved channels.

    :param data: The compressed byte string from the encoder.
    :param channels: The number of audio channels (e.g., 1 for mono, 2 for stereo).
    :return: A byte string of raw, interleaved 16-bit PCM samples.
    """
    # These tables must be identical to the ones used in the encoder.

    if not data or channels < 1:
        return b""

    # The terminator/padding logic is based on the total number of samples (nibbles),
    # so it works independently of the channel count.
    has_terminator = len(data) > 0 and data[-1] == 0xAB  # noqa: PLR2004
    data_to_decode = data[:-1] if has_terminator else data

    # --- Multi-channel state initialization ---
    states = [{"predictor": 0, "step_index": 0} for _ in range(channels)]

    decoded_samples = []
    nibble_index = 0

    # Unpack bytes into nibbles and decode each one
    for byte in data_to_decode:
        nibbles = [(byte >> 4) & 0x0F, byte & 0x0F]
        for code in nibbles:
            # Determine which channel this nibble belongs to
            channel_idx = nibble_index % channels

            # Get the current state for this channel
            state = states[channel_idx]
            predictor = state["predictor"]
            step_index = state["step_index"]

            step = step_size_table[step_index]

            # Reconstruct the difference from the 4-bit code
            reconstructed_diff = step >> 3
            if code & 1:
                reconstructed_diff += step >> 2
            if code & 2:
                reconstructed_diff += step >> 1
            if code & 4:
                reconstructed_diff += step

            # Update the predictor to get the decoded sample
            if code & 8:  # Sign bit
                predictor -= reconstructed_diff
            else:
                predictor += reconstructed_diff

            # Clamp predictor to 16-bit range
            if predictor > 32767:  # noqa: PLR2004
                predictor = 32767
            elif predictor < -32768:  # noqa: PLR2004
                predictor = -32768

            decoded_samples.append(predictor)

            # Update the step index, mirroring the encoder
            step_index += index_table[code & 7]
            if step_index < 0:
                step_index = 0
            elif step_index > 88:  # noqa: PLR2004
                step_index = 88

            # --- Store the updated state for the current channel ---
            state["predictor"] = predictor
            state["step_index"] = step_index

            nibble_index += 1

    # If the original total sample count was odd, the last nibble was padding. Discard it.
    if not has_terminator and len(decoded_samples) > 0:
        decoded_samples.pop()

    # Pack the list of interleaved signed shorts into the final PCM byte string
    if not decoded_samples:
        return b""
    return struct.pack(f"<{len(decoded_samples)}h", *decoded_samples)
