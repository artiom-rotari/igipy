vs.1.0
dp3 r0.x, v1, c8
mul r0, r0.x, c9
add oD0, r0, c10
dp3 r0.x, v0, c4
expp r0, r0.x
rcp oFog, r0.z
add r0, v0, -c7
mul oT0, r0, c13
dp3 r0.x, v0, v0
rsq r0.x, r0.x
mul r0, r0.x, v0
dp3 r1.x, r0, v1
add oD0.w, r1.x, c6.x
mul r1.x, -c5.w, r1.x
mad r1, v1, r1.x, r0
mul r1, r1, c11
add oT1, r1, c12
dp4 oPos.x, v0, c0
dp4 oPos.y, v0, c1
dp4 oPos.z, v0, c2
dp4 oPos.w, v0, c3
