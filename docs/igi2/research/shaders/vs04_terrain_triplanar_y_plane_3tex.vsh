vs.1.0
mov oD0.w, v4.wwwx
mov oFog, v0.w
mul oT0.xy, v0.xz, c11
mul oT1.xy, v0.xz, c12
sub r0, v0, c13
mul oT2.xy, r0, c14
m3x4 r1, v0, c0
add oPos, r1, c14
