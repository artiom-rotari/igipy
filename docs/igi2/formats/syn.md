[Back to README](../../../README.md)

# SYN Format — Lip-Sync Envelope

SYN files store a per-frame mouth-openness envelope used for lip-syncing character speech during cutscenes. Each file is a flat array of float32 amplitude values sampled at ~30 Hz, paired one-to-one with an `.mp3` voice line in the same directory.

## Structure Overview

```
┌────────────────────────────────────────────────────┐
│  float32[0]  float32[1]  float32[2]  ...  float[N] │
│    0.0000      0.0825      0.4652    ...    0.0000  │
└────────────────────────────────────────────────────┘
          No header. No magic bytes. Just floats.
```

There is no header, no version field, and no metadata. The entire file is a contiguous array of little-endian IEEE 754 single-precision floats.

| Property       | Value                                  |
|----------------|----------------------------------------|
| Byte order     | Little-endian                          |
| Element type   | float32 (4 bytes)                      |
| Sample count   | `file_size / 4`                        |
| Value range    | `[0.0, 1.0]`                           |
| Sample rate    | ~30 Hz (29.6–30.0 measured)            |
| Duration       | `sample_count / 30` seconds            |
| First sample   | Always `0.0` (silence at start)        |
| Last sample    | Usually `0.0` (78% of files)           |

## Timing

Every sample represents one animation frame at approximately 30 fps. This was verified by comparing sample counts against MP3 durations (via mutagen) across 12 files spanning all languages and multiple levels:

| File                       | Samples | MP3 duration | Measured rate |
|----------------------------|---------|--------------|---------------|
| cv10_camp_02_guard (en)    | 161     | 5.43 s       | 29.6 Hz       |
| cv10_camp_02_guard (fr)    | 159     | 5.36 s       | 29.7 Hz       |
| cv12_intro_01_white (en)   | 917     | 30.64 s      | 29.9 Hz       |
| cv12_intro_01_white (de)   | 902     | 30.15 s      | 29.9 Hz       |
| cv13_intro_01_white (fr)   | 906     | 30.28 s      | 29.9 Hz       |
| cv14_intro_02_scien (en)   | 297     | 9.98 s       | 29.8 Hz       |

The rate is consistent at ~30 Hz across all languages and levels.

## Envelope Shape

Values form a speech amplitude envelope — bursts of activity correspond to spoken words, with silent gaps between phrases:

```
1.0 |        **                             * *
    |       *  *                           *   *
    |      *    *           * *           *     *
0.5 |     *      *         * * *         *
    |    *        *       *     *       *
    |   *          *     *       *     *
0.0 |--*------------*---*---------*---*-----------
    t=0            t=1           t=2            t=3s
        "Hello"    (pause)    "Command"
```

## File Pairing

Each `.syn` file has a matching `.mp3` file with the same base name in the same directory. Not all `.mp3` files have a `.syn` — voice lines without visible speaker faces (radio chatter, off-screen dialogue) typically lack one.

```
sounds/english/
  cv10_camp_01_pilot.mp3          ← no .syn (radio voice)
  cv10_camp_02_guard.mp3
  cv10_camp_02_guard.syn          ← lip-sync for this MP3
  cv11_intro_01_white.mp3
  cv11_intro_01_white.syn          ← lip-sync for this MP3
  cv11_intro_02_jones.mp3         ← no .syn (off-screen)
```

## Language Variants

The same voice line has separate `.syn` data per language because speech timing differs:

| Language | File                       | Samples | Est. duration |
|----------|----------------------------|---------|---------------|
| English  | cv12_intro_01_white.syn    | 917     | 30.6 s        |
| French   | cv12_intro_01_white.syn    | 910     | 30.3 s        |
| German   | cv12_intro_01_white.syn    | 902     | 30.1 s        |

Languages present in the game data: English, French, German.

## Statistics

| Metric              | Value              |
|---------------------|--------------------|
| Total files         | 369                |
| Unique voice lines  | 123 (× 3 languages) |
| Size range          | 44–5,184 bytes     |
| Sample range        | 11–1,296 samples   |
| Duration range      | ~0.4–43.2 seconds  |
| All sizes div by 4  | Yes                |
| All values in [0,1] | Yes                |
| All start with 0.0  | Yes (100%)         |
| All end with 0.0    | No (78%)           |

## Runtime Usage

The game engine reads the envelope at render time to drive mouth animation:

```
mouth_openness = samples[(int)(current_time * 30)]
```

A value of `0.0` means mouth closed; `1.0` means mouth fully open. Intermediate values produce proportional jaw/lip blending.
