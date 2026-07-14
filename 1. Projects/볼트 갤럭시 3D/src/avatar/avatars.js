import * as THREE from 'three';

// Pluggable avatar registry. Every avatar is 100% code-generated geometry
// (no external model files) and returns a THREE.Group whose local -Z axis
// is "forward" (the direction the shape visually points).

function dartMaterial(color) {
  return new THREE.MeshStandardMaterial({ color, flatShading: true, roughness: 0.4, metalness: 0.2, emissive: color, emissiveIntensity: 0.35 });
}

function buildDart(color = 0x9fe0ff) {
  const group = new THREE.Group();
  const mat = dartMaterial(color);

  const nose = new THREE.ConeGeometry(0.55, 2.3, 4, 1);
  nose.rotateX(-Math.PI / 2);
  const noseMesh = new THREE.Mesh(nose, mat);
  group.add(noseMesh);

  const finGeo = new THREE.ConeGeometry(0.5, 0.9, 3, 1);
  finGeo.rotateX(Math.PI / 2);
  finGeo.translate(0, 0, 1.1);

  const finL = new THREE.Mesh(finGeo, mat);
  finL.scale.set(1, 0.5, 1);
  finL.position.set(-0.55, 0, 0);
  finL.rotation.z = Math.PI / 2.4;
  group.add(finL);

  const finR = finL.clone();
  finR.position.set(0.55, 0, 0);
  finR.rotation.z = -Math.PI / 2.4;
  group.add(finR);

  const finTop = finL.clone();
  finTop.position.set(0, 0.55, 0);
  finTop.rotation.z = 0;
  finTop.rotation.x = Math.PI / 2.4;
  group.add(finTop);

  group.userData.tint = mat;
  return group;
}

function buildBlob(color = 0x9fe0ff) {
  const group = new THREE.Group();
  const geo = new THREE.IcosahedronGeometry(1, 1);
  const pos = geo.attributes.position;
  const v = new THREE.Vector3();
  // deterministic pseudo-noise so the shape is stable across reloads
  let seed = 1337;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    const n = 0.85 + rand() * 0.3;
    v.multiplyScalar(n);
    pos.setXYZ(i, v.x, v.y, v.z * 1.3); // slightly elongated toward forward axis
  }
  geo.computeVertexNormals();
  const mat = dartMaterial(color);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.scale.set(0.85, 0.85, 0.85);
  group.add(mesh);

  // small nose nub so heading is still visible
  const nub = new THREE.Mesh(new THREE.ConeGeometry(0.25, 0.6, 4), mat);
  nub.rotateX(-Math.PI / 2);
  nub.position.set(0, 0, -1.05);
  group.add(nub);

  group.userData.tint = mat;
  return group;
}

const REGISTRY = { dart: buildDart, blob: buildBlob };

export function createAvatar(kind = 'dart', color = 0x9fe0ff) {
  const build = REGISTRY[kind] || REGISTRY.dart;
  return build(color);
}

export function setAvatarColor(avatarGroup, color) {
  if (avatarGroup.userData.tint) {
    avatarGroup.userData.tint.color.setHex(color);
    avatarGroup.userData.tint.emissive.setHex(color);
  }
}
