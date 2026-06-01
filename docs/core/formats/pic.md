[Back to README](../../../README.md)

# PIC Format (`.pic`)

Picture texture. The `.pic` extension is the shared TEX container under a different name — same
`LOOP` signature, same versions, same pixel modes — read by the shared `core` TEX parser and
converted to `.tga` by the same converter.

See **[TEX Format](tex.md)** for the full layout, pixel-mode table, and TGA conversion fidelity
(including which data is and isn't preserved). There is no PIC-specific behavior.
