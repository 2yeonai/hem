import * as THREE from 'three';
import { state, setState, bus } from './state.js';
import { getTheme } from './config/themes.js';
import { GraphScene } from './graph/GraphScene.js';
import { createAvatar } from './avatar/avatars.js';
import { FlightController } from './flight/FlightController.js';
import { createStarfield } from './effects/starfield.js';
import { PostFX } from './effects/postfx.js';
import { UIController } from './ui/ui.js';
import { DiveScene } from './dive/DiveScene.js';

const canvas = document.getElementById('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);

const camera = new THREE.PerspectiveCamera(62, window.innerWidth / window.innerHeight, 0.1, 4000);

const galaxyScene = new THREE.Scene();
let theme = getTheme(state.themeId);
galaxyScene.background = new THREE.Color(theme.background);
galaxyScene.fog = new THREE.Fog(theme.fog.color, theme.fog.near, theme.fog.far);

const ambient = new THREE.AmbientLight(theme.ambient.color, theme.ambient.intensity);
galaxyScene.add(ambient);
const keyLight = new THREE.DirectionalLight(theme.keyLight.color, theme.keyLight.intensity);
keyLight.position.set(200, 300, 150);
galaxyScene.add(keyLight);
const rimLight = new THREE.PointLight(theme.rimLight.color, theme.rimLight.intensity, 2000);
rimLight.position.set(-300, -100, -200);
galaxyScene.add(rimLight);

let stars = createStarfield(theme.starDensity, theme.starColor);
galaxyScene.add(stars);

const galaxyAvatar = createAvatar(state.avatarKind, theme.keyLight.color);
galaxyScene.add(galaxyAvatar);

const flight = new FlightController(camera, galaxyAvatar, canvas);
const ui = new UIController();
const postfx = new PostFX(renderer, galaxyScene, camera, theme);

let graphScene = null;
let diveScene = null;
const noteCache = new Map();

const clock = new THREE.Clock();
const projected = new THREE.Vector3();

// track previous values so we only reheat the force sim (and jitter the
// graph) when a filter/spacing setting actually changed, not on every
// unrelated state update (speed slider, zen mode, hyperdrive, ...).
const prev = {
  showHubs: state.showHubs,
  showAttachments: state.showAttachments,
  linkSpacing: state.linkSpacing,
  themeId: state.themeId
};

async function fetchNote(numId) {
  if (noteCache.has(numId)) return noteCache.get(numId);
  const res = await fetch(`/data/notes/${numId}.json`);
  const data = await res.json();
  noteCache.set(numId, data);
  return data;
}

function applyThemeToScene() {
  theme = getTheme(state.themeId);
  galaxyScene.background.setHex(theme.background);
  galaxyScene.fog.color.setHex(theme.fog.color);
  galaxyScene.fog.near = theme.fog.near;
  galaxyScene.fog.far = theme.fog.far;
  ambient.color.setHex(theme.ambient.color);
  ambient.intensity = theme.ambient.intensity;
  keyLight.color.setHex(theme.keyLight.color);
  keyLight.intensity = theme.keyLight.intensity;
  rimLight.color.setHex(theme.rimLight.color);
  rimLight.intensity = theme.rimLight.intensity;

  galaxyScene.remove(stars);
  stars = createStarfield(theme.starDensity, theme.starColor);
  galaxyScene.add(stars);

  if (graphScene) graphScene.setTheme(theme);
  postfx.setTheme(theme);
}

bus.on('state', (s) => {
  if (s.themeId !== prev.themeId) {
    prev.themeId = s.themeId;
    applyThemeToScene();
  }
  flight.setSpeedFactor(s.speedFactor);

  if (graphScene) {
    if (s.showHubs !== prev.showHubs || s.showAttachments !== prev.showAttachments) {
      prev.showHubs = s.showHubs;
      prev.showAttachments = s.showAttachments;
      graphScene.setVisibility({ showHubs: s.showHubs, showAttachments: s.showAttachments });
    }
    if (s.linkSpacing !== prev.linkSpacing) {
      prev.linkSpacing = s.linkSpacing;
      graphScene.setLinkLength(s.linkSpacing);
    }
  }
});

// --- load graph data, then build the scene graph ---
fetch('/data/graph.json').then((r) => r.json()).then((graph) => {
  graphScene = new GraphScene(galaxyScene, graph, theme);
  graphScene.setLinkLength(state.linkSpacing);
  graphScene.setVisibility({ showHubs: state.showHubs, showAttachments: state.showAttachments });
  diveScene = new DiveScene();
  ui.hideLoading();
  animate();
}).catch((err) => {
  document.getElementById('loading').textContent = '그래프 데이터를 불러오지 못했습니다. npm run build-graph 를 먼저 실행했는지 확인하세요.';
  console.error(err);
});

document.getElementById('theme-select').value = state.themeId;
document.getElementById('toggle-attachments').checked = state.showAttachments;
document.getElementById('toggle-hubs').checked = state.showHubs;
document.getElementById('speed-slider').value = state.speedFactor;
document.getElementById('spacing-slider').value = state.linkSpacing;

// --- hyperdrive (spacebar hold) ---
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !state.hyperdrive) {
    setState({ hyperdrive: true });
    flight.setHyperdrive(true);
  }
});
window.addEventListener('keyup', (e) => {
  if (e.code === 'Space') {
    setState({ hyperdrive: false });
    flight.setHyperdrive(false);
  }
});

// --- crosshair click-to-open (only once pointer is already locked) ---
canvas.addEventListener('mousedown', (e) => {
  if (e.button !== 0 || !flight.pointerLocked || state.diving) return;
  if (!graphScene) return;
  const hit = graphScene.nearestOnRay(camera, 500, 0.05);
  if (hit) {
    ui.openNotePanel(graphScene.nodes[hit.index]);
  }
});

// --- proximity title fade-in + auto-open when very close ---
let lastAutoOpened = null;
function updateProximity() {
  if (!graphScene || state.diving) {
    ui.updateNodeLabel(0, 0, '', false);
    return;
  }
  const near = graphScene.nearestTo(flight.position, 42);
  if (!near) {
    ui.updateNodeLabel(0, 0, '', false);
    lastAutoOpened = null;
    return;
  }
  const node = graphScene.nodes[near.index];
  graphScene.positionOf(near.index, projected);
  projected.project(camera);
  const sx = (projected.x * 0.5 + 0.5) * window.innerWidth;
  const sy = (-projected.y * 0.5 + 0.5) * window.innerHeight;
  const onScreen = projected.z < 1;
  ui.updateNodeLabel(sx, sy, node.t, onScreen);

  if (near.dist < 7 && state.openNoteId === null && lastAutoOpened !== node.n) {
    lastAutoOpened = node.n;
    ui.openNotePanel(node);
  } else if (near.dist > 12) {
    lastAutoOpened = null;
  }
}

// --- dive in / out ---
let savedSnapshot = null;

async function tryEnterDive() {
  if (!graphScene || state.diving) return;
  const hit = graphScene.nearestOnRay(camera, 120, 0.15) || graphScene.nearestTo(flight.position, 42);
  if (!hit) return;
  const node = graphScene.nodes[hit.index];
  if (node.type !== 'note') return;

  const data = await fetchNote(node.n);
  diveScene.buildFor(data.body, state.themeId);
  savedSnapshot = flight.getSnapshot();
  flight.setAvatar(diveScene.avatar);
  flight.resetTo(diveScene.startPosition(), flight.yaw, 0.05);
  postfx.renderPass.scene = diveScene.scene;
  setState({ diving: true, openNoteId: null });
  ui.closeNotePanel();
}

function exitDive() {
  if (!state.diving) return;
  flight.setAvatar(galaxyAvatar);
  if (savedSnapshot) flight.restoreSnapshot(savedSnapshot);
  postfx.renderPass.scene = galaxyScene;
  setState({ diving: false });
}

bus.on('diveRequested', () => {
  if (state.diving) exitDive(); else tryEnterDive();
});
bus.on('escape', () => {
  if (state.diving) exitDive();
});

// --- resize ---
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  postfx.setSize(window.innerWidth, window.innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;

  flight.update(dt);

  if (state.diving) {
    diveScene.update(dt);
  } else if (graphScene) {
    graphScene.update();
    updateProximity();
  }

  postfx.setHyperIntensity(flight.hyperBlend, t);
  postfx.render();
}
