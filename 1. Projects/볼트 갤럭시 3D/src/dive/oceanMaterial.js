import * as THREE from 'three';

const MAX_STRIKES = 3;

export function createOceanMaterial(textTexture, palette) {
  const uniforms = {
    uTime: { value: 0 },
    uTexture: { value: textTexture },
    uDeep: { value: new THREE.Color(palette.deep) },
    uShallow: { value: new THREE.Color(palette.shallow) },
    uGlow: { value: new THREE.Color(palette.glow) },
    uStrikePos: { value: Array.from({ length: MAX_STRIKES }, () => new THREE.Vector3()) },
    uStrikeTime: { value: new Float32Array(MAX_STRIKES).fill(-1000) },
    fogColor: { value: new THREE.Color(0x000000) },
    fogNear: { value: 1 },
    fogFar: { value: 1000 }
  };

  const material = new THREE.ShaderMaterial({
    uniforms,
    fog: true,
    vertexShader: /* glsl */`
      uniform float uTime;
      uniform vec3 uStrikePos[${MAX_STRIKES}];
      uniform float uStrikeTime[${MAX_STRIKES}];
      varying vec2 vUv;
      varying vec3 vViewPos;

      #include <fog_pars_vertex>

      void main() {
        vUv = uv * vec2(26.0, 26.0);
        vec3 pos = position;

        float amb = sin(pos.x * 0.045 + uTime * 0.8) * 0.35
                  + cos(pos.z * 0.05 - uTime * 0.65) * 0.35;
        pos.y += amb;

        vec2 scatter = vec2(0.0);
        for (int i = 0; i < ${MAX_STRIKES}; i++) {
          float age = uTime - uStrikeTime[i];
          if (age > 0.0 && age < 1.6) {
            vec2 d = pos.xz - uStrikePos[i].xz;
            float dist = length(d) + 0.001;
            float ring = dist - age * 42.0;
            float wave = exp(-abs(ring) * 0.05) * exp(-age * 1.3);
            pos.y += wave * 6.5;
            scatter += normalize(d) * wave * 3.5;
          }
        }
        pos.xz += scatter;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        vViewPos = mvPosition.xyz;
        gl_Position = projectionMatrix * mvPosition;

        #include <fog_vertex>
      }
    `,
    fragmentShader: /* glsl */`
      uniform sampler2D uTexture;
      uniform vec3 uDeep;
      uniform vec3 uShallow;
      uniform vec3 uGlow;
      uniform float uTime;
      varying vec2 vUv;
      varying vec3 vViewPos;

      #include <fog_pars_fragment>

      void main() {
        vec3 fdx = dFdx(vViewPos);
        vec3 fdy = dFdy(vViewPos);
        vec3 normal = normalize(cross(fdx, fdy));
        vec3 viewDir = normalize(-vViewPos);
        float fresnel = pow(1.0 - clamp(dot(normal, viewDir), 0.0, 1.0), 2.2);

        vec2 scrollUv = vUv + vec2(uTime * 0.01, uTime * 0.006);
        vec4 tex = texture2D(uTexture, scrollUv);
        float glowPulse = 0.75 + 0.25 * sin(uTime * 1.4 + vUv.x * 6.0);

        vec3 base = mix(uDeep, uShallow, fresnel);
        vec3 color = base + uGlow * tex.a * glowPulse * 1.4;
        color += uGlow * fresnel * 0.25;

        gl_FragColor = vec4(color, 1.0);
        #include <fog_fragment>
      }
    `
  });

  material.userData.setStrike = (index, pos, time) => {
    uniforms.uStrikePos.value[index % MAX_STRIKES].copy(pos);
    uniforms.uStrikeTime.value[index % MAX_STRIKES] = time;
  };
  material.userData.maxStrikes = MAX_STRIKES;

  return material;
}
