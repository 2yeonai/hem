import * as THREE from 'three';
import { createStarfield } from '../effects/starfield.js';
import { createOceanMaterial } from './oceanMaterial.js';
import { makeTextTileTexture } from './textTexture.js';
import { createAuroraCurtains } from './aurora.js';
import { LightningSystem } from './lightning.js';
import { createAvatar } from '../avatar/avatars.js';

const PALETTES = {
  deepspace: { deep: 0x020814, shallow: 0x0c3a52, glow: 0xbfe8ff },
  nebula: { deep: 0x140620, shallow: 0x4a1a5c, glow: 0xffd6f2 }
};

export class DiveScene {
  constructor() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x020208);
    this.scene.fog = new THREE.Fog(0x020208, 120, 1100);

    this.ambient = new THREE.AmbientLight(0x5f7aa8, 0.5);
    this.scene.add(this.ambient);
    this.moon = new THREE.DirectionalLight(0xdfe8ff, 0.9);
    this.moon.position.set(-120, 220, -80);
    this.scene.add(this.moon);

    this.stars = createStarfield(4000, 0xffffff);
    this.scene.add(this.stars);

    this.oceanGroup = new THREE.Group();
    this.scene.add(this.oceanGroup);

    this.avatarKind = 'blob';
    this.avatar = createAvatar(this.avatarKind, 0xbfe8ff);
    this.scene.add(this.avatar);

    this._built = false;
  }

  setAvatarKind(kind) {
    if (kind === this.avatarKind) return;
    this.scene.remove(this.avatar);
    this.avatarKind = kind;
    this.avatar = createAvatar(kind, 0xbfe8ff);
    this.scene.add(this.avatar);
  }

  // (re)builds ocean + aurora from a specific note's text, and applies theme palette
  buildFor(noteBody, themeId) {
    if (this.ocean) {
      this.oceanGroup.remove(this.ocean);
      this.ocean.geometry.dispose();
      this.ocean.material.dispose();
    }
    if (this.auroraGroup) {
      this.oceanGroup.remove(this.auroraGroup);
    }
    if (this.lightning) this.lightning.dispose();

    const palette = PALETTES[themeId] || PALETTES.deepspace;
    const tex = makeTextTileTexture(noteBody);
    tex.repeat.set(1, 1);
    const mat = createOceanMaterial(tex, palette);
    const geo = new THREE.PlaneGeometry(2600, 2600, 140, 140);
    geo.rotateX(-Math.PI / 2);
    this.ocean = new THREE.Mesh(geo, mat);
    this.oceanGroup.add(this.ocean);

    const aurora = createAuroraCurtains(noteBody);
    this.auroraGroup = aurora.group;
    this._auroraUpdate = aurora.update;
    this.oceanGroup.add(this.auroraGroup);

    this.lightning = new LightningSystem(this.oceanGroup, mat, 260);

    this.scene.fog.color.setHex(palette.deep);
    this.scene.background.setHex(palette.deep);

    this._built = true;
    this._t0 = performance.now() / 1000;
  }

  update(dt) {
    if (!this._built) return;
    const t = performance.now() / 1000 - this._t0;
    this.ocean.material.uniforms.uTime.value = t;
    this._auroraUpdate(t);
    this.lightning.update(dt, t);
  }

  startPosition() {
    return new THREE.Vector3(0, 26, 90);
  }
}
