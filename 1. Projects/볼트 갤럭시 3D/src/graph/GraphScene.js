import * as THREE from 'three';
import { ForceSim } from './ForceSim.js';
import { colorForNode } from '../config/themes.js';

const TYPE_SCALE = { note: 1.0, hub: 1.3, attachment: 0.6 };

function radiusFor(node) {
  const base = 1.5 + Math.sqrt(node.deg + 1) * 0.85;
  return Math.min(base, 8.5) * (TYPE_SCALE[node.type] || 1);
}

export class GraphScene {
  constructor(scene, graph, theme) {
    this.scene = scene;
    this.graph = graph; // { nodes, edges, stats }
    this.nodes = graph.nodes;
    this.edges = graph.edges;
    this.count = this.nodes.length;

    this.sim = new ForceSim(this.count, this.edges);
    this.radii = new Float32Array(this.count);
    for (let i = 0; i < this.count; i++) this.radii[i] = radiusFor(this.nodes[i]);

    this.visible = new Uint8Array(this.count).fill(1);
    this._recomputeVisibility({ showHubs: true, showAttachments: false }, true);

    const geo = new THREE.IcosahedronGeometry(1, 1);
    const mat = new THREE.MeshStandardMaterial({
      roughness: 0.35, metalness: 0.15, emissiveIntensity: 0.55, flatShading: true
    });
    this.mesh = new THREE.InstancedMesh(geo, mat, this.count);
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);

    const edgeGeo = new THREE.BufferGeometry();
    const edgePositions = new Float32Array(this.edges.length * 2 * 3);
    edgeGeo.setAttribute('position', new THREE.BufferAttribute(edgePositions, 3));
    const edgeMat = new THREE.LineBasicMaterial({ transparent: true, opacity: 0.35, color: 0x3a5a8f });
    this.edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
    this.edgeLines.frustumCulled = false;
    this.scene.add(this.edgeLines);

    this.setTheme(theme);
    this._tmpMatrix = new THREE.Matrix4();
    this._tmpQuat = new THREE.Quaternion();
    this._tmpScale = new THREE.Vector3();
    this._tmpPos = new THREE.Vector3();
  }

  setTheme(theme) {
    this.theme = theme;
    const color = new THREE.Color();
    for (let i = 0; i < this.count; i++) {
      color.setHex(colorForNode(theme, this.nodes[i]));
      this.mesh.setColorAt(i, color);
    }
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
    this.mesh.material.emissive = new THREE.Color(theme.hubColor).multiplyScalar(0.15);
    this.edgeLines.material.color.setHex(theme.edgeColor);
    this.edgeLines.material.opacity = theme.edgeOpacity;
  }

  _recomputeVisibility({ showHubs, showAttachments }, silent) {
    const visibleSet = new Set();
    for (let i = 0; i < this.count; i++) {
      const t = this.nodes[i].type;
      const on = t === 'note' || (t === 'hub' && showHubs) || (t === 'attachment' && showAttachments);
      this.visible[i] = on ? 1 : 0;
      if (on) visibleSet.add(i);
    }
    this._visibleSet = visibleSet;
    if (!silent) this.sim.setActiveMask(visibleSet);
  }

  setVisibility(flags) {
    this._recomputeVisibility(flags, false);
  }

  setLinkLength(len) {
    this.sim.setLinkLength(len);
  }

  update() {
    this.sim.tick();
    const { x, y, z } = this.sim;
    for (let i = 0; i < this.count; i++) {
      const s = this.visible[i] ? this.radii[i] : 0.0001;
      this._tmpPos.set(x[i], y[i], z[i]);
      this._tmpScale.set(s, s, s);
      this._tmpMatrix.compose(this._tmpPos, this._tmpQuat, this._tmpScale);
      this.mesh.setMatrixAt(i, this._tmpMatrix);
    }
    this.mesh.instanceMatrix.needsUpdate = true;

    const pos = this.edgeLines.geometry.attributes.position.array;
    for (let e = 0; e < this.edges.length; e++) {
      const [a, b] = this.edges[e];
      const ok = this.visible[a] && this.visible[b];
      const i6 = e * 6;
      if (ok) {
        pos[i6] = x[a]; pos[i6 + 1] = y[a]; pos[i6 + 2] = z[a];
        pos[i6 + 3] = x[b]; pos[i6 + 4] = y[b]; pos[i6 + 5] = z[b];
      } else {
        pos[i6] = pos[i6 + 3] = x[a];
        pos[i6 + 1] = pos[i6 + 4] = y[a];
        pos[i6 + 2] = pos[i6 + 5] = z[a];
      }
    }
    this.edgeLines.geometry.attributes.position.needsUpdate = true;
  }

  positionOf(i, out) {
    out.set(this.sim.x[i], this.sim.y[i], this.sim.z[i]);
    return out;
  }

  // nearest visible node to a world point, within maxDist. returns {index, dist} or null
  nearestTo(point, maxDist) {
    let best = -1, bestD = maxDist;
    const { x, y, z } = this.sim;
    for (let i = 0; i < this.count; i++) {
      if (!this.visible[i]) continue;
      const dx = x[i] - point.x, dy = y[i] - point.y, dz = z[i] - point.z;
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz) - this.radii[i];
      if (d < bestD) { bestD = d; best = i; }
    }
    return best === -1 ? null : { index: best, dist: bestD };
  }

  // nearest visible node to the camera's forward ray (crosshair targeting)
  nearestOnRay(camera, maxDist, maxAngle = 0.06) {
    const forward = new THREE.Vector3();
    camera.getWorldDirection(forward);
    const camPos = camera.position;
    let best = -1, bestScore = Infinity;
    const { x, y, z } = this.sim;
    const toNode = new THREE.Vector3();
    for (let i = 0; i < this.count; i++) {
      if (!this.visible[i]) continue;
      toNode.set(x[i] - camPos.x, y[i] - camPos.y, z[i] - camPos.z);
      const dist = toNode.length();
      if (dist > maxDist || dist < 0.001) continue;
      toNode.normalize();
      const angle = forward.angleTo(toNode);
      const angularSlack = maxAngle + this.radii[i] / dist;
      if (angle < angularSlack) {
        const score = dist * (angle / angularSlack + 0.2);
        if (score < bestScore) { bestScore = score; best = i; }
      }
    }
    return best === -1 ? null : { index: best };
  }
}
