import * as THREE from 'three';
import { makeAuroraTexture } from './textTexture.js';

const AURORA_COLORS = [0x6bffb0, 0x7ad9ff, 0xb98bff, 0xff8fd6];

export function createAuroraCurtains(noteText) {
  const group = new THREE.Group();
  const sheets = [];
  const count = 4;

  for (let i = 0; i < count; i++) {
    const width = 260 + Math.random() * 140;
    const height = 140 + Math.random() * 80;
    const segX = 28, segY = 14;
    const geo = new THREE.PlaneGeometry(width, height, segX, segY);
    const tex = makeAuroraTexture(noteText, i * 37);
    const mat = new THREE.MeshBasicMaterial({
      map: tex, color: AURORA_COLORS[i % AURORA_COLORS.length],
      transparent: true, opacity: 0.4, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.set((Math.random() - 0.5) * 260, 130 + i * 22, -220 - i * 60 + (Math.random() - 0.5) * 60);
    mesh.rotation.y = (Math.random() - 0.5) * 0.6;
    mesh.userData.basePos = geo.attributes.position.array.slice();
    mesh.userData.phase = Math.random() * 10;
    mesh.userData.speedScroll = 0.02 + Math.random() * 0.02;
    group.add(mesh);
    sheets.push(mesh);
  }

  function update(time) {
    for (const mesh of sheets) {
      const pos = mesh.geometry.attributes.position;
      const base = mesh.userData.basePos;
      const phase = mesh.userData.phase;
      for (let i = 0; i < pos.count; i++) {
        const bx = base[i * 3], by = base[i * 3 + 1], bz = base[i * 3 + 2];
        const wave = Math.sin(by * 0.03 + time * 0.6 + phase) * 14
          + Math.sin(by * 0.08 - time * 0.35 + phase * 1.7) * 6;
        pos.setXYZ(i, bx, by, bz + wave);
      }
      pos.needsUpdate = true;
      mesh.material.map.offset.y = (time * mesh.userData.speedScroll) % 1;
    }
  }

  return { group, update };
}
