import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

const HyperShader = {
  uniforms: {
    tDiffuse: { value: null },
    uIntensity: { value: 0 },
    uTime: { value: 0 }
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float uIntensity;
    uniform float uTime;
    varying vec2 vUv;

    void main() {
      vec2 center = vec2(0.5, 0.5);
      vec2 toCenter = vUv - center;
      float dist = length(toCenter);

      vec4 color = texture2D(tDiffuse, vUv);

      if (uIntensity > 0.001) {
        vec2 dir = normalize(toCenter + 1e-5);
        float samples = 10.0;
        vec4 streak = vec4(0.0);
        float total = 0.0;
        for (float i = 0.0; i < 10.0; i += 1.0) {
          float t = i / samples;
          float pull = t * uIntensity * 0.55 * (0.4 + dist);
          vec2 sampleUv = vUv - dir * pull;
          float w = 1.0 - t;
          streak += texture2D(tDiffuse, clamp(sampleUv, 0.0, 1.0)) * w;
          total += w;
        }
        streak /= total;
        color = mix(color, streak, clamp(uIntensity * 1.1, 0.0, 1.0));

        float vign = smoothstep(0.15, 0.85, dist);
        color.rgb *= mix(1.0, 1.0 - vign * 0.85, uIntensity);

        float flicker = 0.5 + 0.5 * sin(uTime * 40.0 + dist * 30.0);
        color.rgb += vec3(0.7, 0.85, 1.0) * uIntensity * flicker * 0.06 * (dist);
      }

      gl_FragColor = color;
    }
  `
};

export class PostFX {
  constructor(renderer, scene, camera, theme) {
    this.renderer = renderer;
    this.composer = new EffectComposer(renderer);
    this.renderPass = new RenderPass(scene, camera);
    this.composer.addPass(this.renderPass);

    this.bloomPass = new UnrealBloomPass(new THREE.Vector2(1, 1), theme.bloom.strength, theme.bloom.radius, theme.bloom.threshold);
    this.composer.addPass(this.bloomPass);

    this.hyperPass = new ShaderPass(HyperShader);
    this.composer.addPass(this.hyperPass);

    this.outputPass = new OutputPass();
    this.composer.addPass(this.outputPass);

    this.setSize(window.innerWidth, window.innerHeight);
  }

  setTheme(theme) {
    this.bloomPass.strength = theme.bloom.strength;
    this.bloomPass.radius = theme.bloom.radius;
    this.bloomPass.threshold = theme.bloom.threshold;
  }

  setHyperIntensity(v, t) {
    this.hyperPass.uniforms.uIntensity.value = v;
    this.hyperPass.uniforms.uTime.value = t;
  }

  setSize(w, h) {
    this.composer.setSize(w, h);
    this.bloomPass.setSize(w, h);
  }

  render() {
    this.composer.render();
  }
}
