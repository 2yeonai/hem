// Lightweight custom 3D force-directed layout (springs + repulsion),
// modeled loosely on d3-force's alpha-cooling approach so the graph
// settles and then holds still, but can be "reheated" on demand.

export class ForceSim {
  constructor(nodeCount, edges) {
    this.count = nodeCount;
    this.edges = edges; // array of [a,b]

    this.x = new Float32Array(nodeCount);
    this.y = new Float32Array(nodeCount);
    this.z = new Float32Array(nodeCount);
    this.vx = new Float32Array(nodeCount);
    this.vy = new Float32Array(nodeCount);
    this.vz = new Float32Array(nodeCount);

    for (let i = 0; i < nodeCount; i++) {
      const r = 120 + Math.random() * 180;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      this.x[i] = r * Math.sin(phi) * Math.cos(theta);
      this.y[i] = r * Math.sin(phi) * Math.sin(theta) * 0.6;
      this.z[i] = r * Math.cos(phi);
    }

    this.linkLength = 90;
    this.active = new Uint8Array(nodeCount).fill(1);
    this.activeIndices = [];
    for (let i = 0; i < nodeCount; i++) this.activeIndices.push(i);
    this.activeEdges = edges.slice();

    this.alpha = 1;
    this.alphaMin = 0.006;
    this.alphaDecay = 0.018;
    this.velocityDecay = 0.72;
    this.repelStrength = 2400;
    this.springStrength = 0.09;
    this.centerStrength = 0.006;
  }

  setLinkLength(len) {
    this.linkLength = len;
    this.reheat();
  }

  setActiveMask(visibleSet) {
    this.activeIndices = [];
    for (let i = 0; i < this.count; i++) {
      const on = visibleSet.has(i);
      this.active[i] = on ? 1 : 0;
      if (on) this.activeIndices.push(i);
    }
    this.activeEdges = this.edges.filter(([a, b]) => this.active[a] && this.active[b]);
    this.reheat();
  }

  reheat() {
    this.alpha = 1;
  }

  settled() {
    return this.alpha < this.alphaMin;
  }

  tick() {
    if (this.alpha < this.alphaMin) return;
    const { x, y, z, vx, vy, vz, activeIndices, activeEdges } = this;
    const n = activeIndices.length;
    const alpha = this.alpha;

    for (let ii = 0; ii < n; ii++) {
      const i = activeIndices[ii];
      let fx = 0, fy = 0, fz = 0;
      for (let jj = 0; jj < n; jj++) {
        if (ii === jj) continue;
        const j = activeIndices[jj];
        let dx = x[i] - x[j], dy = y[i] - y[j], dz = z[i] - z[j];
        let d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < 0.01) { dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); dz = (Math.random() - 0.5); d2 = 1; }
        if (d2 > 90000) continue;
        const d = Math.sqrt(d2);
        const f = (this.repelStrength / d2) * alpha;
        fx += (dx / d) * f;
        fy += (dy / d) * f;
        fz += (dz / d) * f;
      }
      vx[i] += fx;
      vy[i] += fy;
      vz[i] += fz;
    }

    for (let e = 0; e < activeEdges.length; e++) {
      const [a, b] = activeEdges[e];
      let dx = x[b] - x[a], dy = y[b] - y[a], dz = z[b] - z[a];
      let d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 0.001;
      const diff = (d - this.linkLength) / d;
      const f = diff * this.springStrength * alpha;
      const ox = dx * f, oy = dy * f, oz = dz * f;
      vx[a] += ox; vy[a] += oy; vz[a] += oz;
      vx[b] -= ox; vy[b] -= oy; vz[b] -= oz;
    }

    for (let ii = 0; ii < n; ii++) {
      const i = activeIndices[ii];
      vx[i] -= x[i] * this.centerStrength * alpha;
      vy[i] -= y[i] * this.centerStrength * alpha;
      vz[i] -= z[i] * this.centerStrength * alpha;
    }

    for (let ii = 0; ii < n; ii++) {
      const i = activeIndices[ii];
      vx[i] *= this.velocityDecay;
      vy[i] *= this.velocityDecay;
      vz[i] *= this.velocityDecay;
      x[i] += vx[i];
      y[i] += vy[i];
      z[i] += vz[i];
    }

    this.alpha *= (1 - this.alphaDecay);
  }
}
