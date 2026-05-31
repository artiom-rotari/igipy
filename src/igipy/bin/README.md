# gconv.exe

`gconv.exe` is the command-line converter shipped with *I.G.I-2: Covert Strike*.
Together with `gconvapi.dll` and `vqdll.dll`, it converts common files (e.g., WAV) into the game’s proprietary formats.

## Package contents

"`
gconv.exe
gconvapi.dll
vqdll.dll
"`

## Usage

`gconv.exe` executes a `.qsc` script containing one or more conversion commands.

"`qsc
// example_01.qsc
ConvertSoundFile("m1_ambience_regular.wav", "m1_ambience_encoded.wav", 0);
"`

Run the tool from the folder that holds the three binaries and your input file:

"`powershell
PS> .\gconv.exe example_01.qsc
"`

### Result

* **m1\_ambience\_regular.wav** – original PCM WAV
* **m1\_ambience\_encoded.wav** – encoded game format

> **Tip:** Add more `ConvertSoundFile` lines to the same script to batch-convert multiple files.
