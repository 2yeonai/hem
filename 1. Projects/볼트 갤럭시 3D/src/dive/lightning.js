import * as THREE from 'three';

function jaggedPoints(start, end, segments, jitter) {
  const pts = [start.clone()];
  for (let i = 1; i < segments; i++) {
    const t = i / segments;
    const p = start.clone().lerp(end, t);
    p.x += (Math.random() - 0.5) * jitter * (1 - t * 0.4);
    p.z += (Math.random() - 0.5) * jitter * (1 - t * 0.4);
    pts.push(p);
  }
  pts.push(end.clone());
  return pts;
}

export class LightningSystem {
  constructor(scene, oceanMaterial, bounds = 220) {
    this.scene = scene;
    this.oceanMaterial = oceanMaterial;
    this.bounds = bounds;
    this.strikeIndex = 0;
    this.nextStrikeAt = performance.now() / 1000 + 2 + Math.random() * 3;
    this.activeBolts = [];

    this.flash = new THREE.PointLight(0xcfe8ff, 0, 400, 2);
    this.flash.position.set(0, 40, 0);
    scene.add(this.flash);
  }

  _spawnBolt(strikePoint) {
    const start = new THREE.Vector3(strikePoint.x + (Math.random() - 0.5) * 20, 160, strikePoint.z + (Math.random() - 0.5) * 20);
    const pts = jaggedPoints(start, strikePoint, 9, 14);
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({ color: 0xdff2ff, transparent: true, opacity: 1 });
    const line = new THREE.Line(geo, mat);
    this.scene.add(line);
    this.activeBolts.push({ line, born: performance.now() / 1000 });
  }

  update(dt, time) {
    if (time >= this.nextStrikeAt) {
      const strikePoint = new THREE.Vector3(
        (Math.random() - 0.5) * this.bounds,
        0,
        (Math.random() - 0.5) * this.bounds
      );
      this._spawnBolt(strikePoint);
      this.oceanMaterial.userData.setStrike(this.strikeIndex, strikePoint, time);
      this.strikeIndex = (this.strikeIndex + 1) % this.oceanMaterial.userData.maxStrikes;

      this.flash.position.set(strikePoint.x, 30, strikePoint.z);
      this.flash.intensity = 6;

      this.nextStrikeAt = time + 2.5 + Math.random() * 3.5;
    }

    if (this.flash.intensity > 0) {
      this.flash.intensity = Math.max(0, this.flash.intensity - dt * 14);
    }

    for (let i = this.activeBolts.length - 1; i >= 0; i--) {
      const b = this.activeBolts[i];
      const age = time - b.born;
      if (age > 0.18) {
        this.scene.remove(b.line);
        b.line.geometry.dispose();
        b.line.material.dispose();
        this.activeBolts.splice(i, 1);
      } else {
        b.line.material.opacity = 1 - age / 0.18;
      }
    }
  }

  dispose() {
    this.scene.remove(this.flash);
    for (const b of this.activeBolts) {
      this.scene.remove(b.line);
      b.line.geometry.dispose();
      b.line.material.dispose();
    }
  }
}
