vs.1.0
dp3 r0.x, v0, c4
expp r1.x, r0.x
rcp oFog, r1.x
dp3 r0.x, v0, v0
rsq r0.x, r0.x
mul r0, r0.x, -v0
dp3 r1.w, v1, c8
mul r1, c9, r1.w
mul r1, r1, c20
add r1, r1, c10
dp3 r2.x, r0, v1
add oT0.xy, v0.xy, -c7.xy
add r3.x, c5.z, -r2.x
mul r4.x, r3.x, r3.x
mul r4.x, r4.x, r4.x
mul r4.x, r4.x, r3.x
mad r3.w, r4.x, c14.y, c14.x
add r3.x, c5.z, -r3.w
mov oD0.xyz, r3.www
mul oD0.w, r3.x, v2.x
add r4.x, c5.z, -v2.x
mov r4.x, c5.z
add r6, r0, c8
dp3 r6.w, r6, r6
rsq r6.w, r6.w
mul r6, r6, r6.w
dp3 r7.w, r6, v1
mul r7.x, r7.w, r7.w
mul r7.x, r7.x, r7.x
mul r7.x, r7.x, r7.x
mul r7.x, r7.x, r7.w
mul r8, c21, r7.x
mul r8, r8, c9
mul r5, r1, r3.x
mad r9, r8, r3.w, r5
mul oD1, r9, r4.x
m4x4 oPos, v0, c0
