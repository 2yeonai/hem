import * as THREE from 'three';
import { clamp, lerp } from '../util.js';

const UP = new THREE.Vector3(0, 1, 0);

// Third-person, flight-sim style controller.
// - mouse: yaw (heading) + pitch (view tilt only, no roll)
// - WASD: level-heading thrust + strafe
// - R/F: ascend / descend
// - Space (external flag): hyperdrive surge, handled via setHyperdrive()
export class FlightController {
  constructor(camera, avatarGroup, domElement) {
    this.camera = camera;
    this.avatar = avatarGroup;
    this.dom = domElement;

    this.yaw = 0;
    this.pitch = 0.12;
    this.position = new THREE.Vector3(0, 20, 260);
    this.velocity = new THREE.Vector3();

    this.keys = new Set();
    this.pointerLocked = false;
    this.sensitivity = 0.0022;

    this.baseMaxSpeed = 55;
    this.speedFactor = 0.25;
    this.accel = 90;
    this.damping = 2.2; // higher = more friction

    this.hyperTarget = 0;
    this.hyperBlend = 0;

    this._bind();

    this.cameraOffset = new THREE.Vector3(0, 4.2, 13);
    this._tmpFwd = new THREE.Vector3();
    this._tmpRight = new THREE.Vector3();
    this._tmpThrust = new THREE.Vector3();
    this._tmpCamPos = new THREE.Vector3();
  }

  _bind() {
    this.dom.addEventListener('click', () => {
      if (!this.pointerLocked) this.dom.requestPointerLock();
    });
    document.addEventListener('pointerlockchange', () => {
      this.pointerLocked = document.pointerLockElement === this.dom;
    });
    document.addEventListener('mousemove', (e) => {
      if (!this.pointerLocked) return;
      this.yaw -= e.movementX * this.sensitivity;
      this.pitch -= e.movementY * this.sensitivity;
      this.pitch = clamp(this.pitch, -1.1, 1.1);
    });
    window.addEventListener('keydown', (e) => this.keys.add(e.code));
    window.addEventListener('keyup', (e) => this.keys.delete(e.code));
  }

  setSpeedFactor(f) { this.speedFactor = f; }
  setHyperdrive(on) { this.hyperTarget = on ? 1 : 0; }
  setAvatar(group) { this.avatar = group; }

  getSnapshot() {
    return {
      yaw: this.yaw,
      pitch: this.pitch,
      position: this.position.clone(),
      velocity: this.velocity.clone()
    };
  }

  restoreSnapshot(s) {
    this.yaw = s.yaw;
    this.pitch = s.pitch;
    this.position.copy(s.position);
    this.velocity.copy(s.velocity);
  }

  resetTo(position, yaw, pitch) {
    this.position.copy(position);
    this.velocity.set(0, 0, 0);
    if (yaw !== undefined) this.yaw = yaw;
    if (pitch !== undefined) this.pitch = pitch;
  }

  get maxSpeed() {
    const base = 6 + this.baseMaxSpeed * this.speedFactor;
    const hyperMax = base * 7;
    return lerp(base, hyperMax, this.hyperBlend);
  }

  update(dt) {
    dt = Math.min(dt, 0.05);
    this.hyperBlend += ((this.hyperTarget - this.hyperBlend) * Math.min(1, dt * 3.2));

    this._tmpFwd.set(0, 0, -1).applyAxisAngle(UP, this.yaw);
    this._tmpRight.set(1, 0, 0).applyAxisAngle(UP, this.yaw);

    this._tmpThrust.set(0, 0, 0);
    const k = this.keys;
    if (k.has('KeyW')) this._tmpThrust.add(this._tmpFwd);
    if (k.has('KeyS')) this._tmpThrust.addScaledVector(this._tmpFwd, -1);
    if (k.has('KeyD')) this._tmpThrust.add(this._tmpRight);
    if (k.has('KeyA')) this._tmpThrust.addScaledVector(this._tmpRight, -1);
    if (this._tmpThrust.lengthSq() > 0) this._tmpThrust.normalize();

    if (k.has('KeyR')) this._tmpThrust.y += 1;
    if (k.has('KeyF')) this._tmpThrust.y -= 1;

    if (this.hyperBlend > 0.01) {
      this._tmpThrust.lerp(this._tmpFwd, this.hyperBlend * 0.9);
    }

    this.velocity.addScaledVector(this._tmpThrust, this.accel * dt);

    const speed = this.velocity.length();
    const max = this.maxSpeed;
    if (speed > max) this.velocity.multiplyScalar(max / speed);

    const dampFactor = Math.exp(-this.damping * dt);
    this.velocity.multiplyScalar(dampFactor);

    this.position.addScaledVector(this.velocity, dt);

    this.avatar.position.copy(this.position);
    this.avatar.rotation.set(0, this.yaw, 0);
    const noseTilt = clamp(this.velocity.y * -0.02, -0.35, 0.35);
    this.avatar.rotation.x = noseTilt;

    const offset = this.cameraOffset.clone();
    offset.applyAxisAngle(new THREE.Vector3(1, 0, 0), this.pitch);
    offset.applyAxisAngle(UP, this.yaw);
    this._tmpCamPos.copy(this.position).add(offset);
    this.camera.position.lerp(this._tmpCamPos, 1 - Math.exp(-8 * dt));
    this.camera.lookAt(this.position);

    return { speed, max, hyperBlend: this.hyperBlend };
  }
}
