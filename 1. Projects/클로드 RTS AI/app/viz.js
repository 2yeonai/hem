/* RTS 3D 뷰어 엔진 — Three.js(ES 모듈, r149) 기반 절차적 포즈블 마네킹.
 * - 근육 실제 형상(Z-Anatomy 메시, app/assets/muscles.glb)은 GLTFLoader로 로드해 선택 시 오버레이.
 * - 자세 프리셋(서기/앉기/누움/엎드림/옆누움)으로 대상자 자세를 재현.
 * - 타깃 부위는 고채도(빨강/주황) + 발광, 나머지는 저채도 반투명으로 대비. */
import * as THREE from "three";
import { GLTFLoader } from "./vendor/loaders/GLTFLoader.js";

// app.js가 "3D 엔진 로드됨" 판정에 window.THREE 존재 여부를 쓰고 있어 하위호환으로 노출
window.THREE = THREE;

window.RTSViz = (function () {
  "use strict";
  var scene, camera, renderer, rootPivot, mannequin, seg = {}, raf = null;
  var canvas, dragging = false, lastX = 0, lastY = 0, yaw = 0.5, pitch = 0.05, dist = 3.2;
  var handSprite = null, arrowHelper = null, labelSprite = null;
  var mounted = false;
  var currentPoseTag = "서기", lastZAnatomy = "";

  var COL_DIM = 0x9aa0aa, COL_BASE = 0xc9ccd2, COL_TARGET = 0xff5a2a, EMIS_TARGET = 0xd82f10;

  var BILATERAL = {
    upperArm: ["upperArmL", "upperArmR"], foreArm: ["foreArmL", "foreArmR"],
    hand: ["handL", "handR"], thigh: ["thighL", "thighR"],
    shin: ["shinL", "shinR"], foot: ["footL", "footR"]
  };

  // 자세 프리셋: 각 관절 그룹 회전(라디안) + root 위치/회전
  var POSES = {
    "서기": { root: { pos: [0, 0, 0], rot: [0, 0, 0] } },
    "앉기": {
      root: { pos: [0, -0.42, 0], rot: [0, 0, 0] },
      thighL: [Math.PI / 2, 0, 0], thighR: [Math.PI / 2, 0, 0],
      shinL: [-Math.PI / 2, 0, 0], shinR: [-Math.PI / 2, 0, 0],
      footL: [Math.PI / 2, 0, 0], footR: [Math.PI / 2, 0, 0]
    },
    "누움": {
      root: { pos: [0, -0.55, 0], rot: [-Math.PI / 2, 0, 0] },
      thighL: [Math.PI / 3, 0, 0], thighR: [Math.PI / 3, 0, 0],
      shinL: [-Math.PI / 2.1, 0, 0], shinR: [-Math.PI / 2.1, 0, 0]
    },
    "엎드림": {
      root: { pos: [0, -0.55, 0], rot: [Math.PI / 2, 0, 0] }
    },
    "옆누움": {
      root: { pos: [0, -0.5, 0], rot: [0, 0, Math.PI / 2] },
      thighL: [Math.PI / 5, 0, 0], thighR: [Math.PI / 5, 0, 0],
      shinL: [-Math.PI / 4, 0, 0], shinR: [-Math.PI / 4, 0, 0]
    }
  };

  function mat(color, opts) {
    opts = opts || {};
    return new THREE.MeshStandardMaterial({
      color: color, roughness: 0.72, metalness: 0.02,
      transparent: !!opts.transparent, opacity: opts.opacity == null ? 1 : opts.opacity,
      emissive: opts.emissive || 0x000000, emissiveIntensity: opts.emissiveIntensity || 0
    });
  }

  // 관절 그룹 + 세그먼트 메시를 만든다. pivot은 근위(관절), 메시는 원위로 length만큼 뻗음.
  function limb(parent, key, x, y, z, len, rad, axis) {
    var g = new THREE.Group();
    g.position.set(x, y, z);
    parent.add(g);
    var geo = new THREE.CapsuleGeometry(rad, len, 6, 12);
    var m = new THREE.Mesh(geo, mat(COL_BASE));
    // 기본: 아래(-Y)로 뻗도록 메시를 내려 배치
    m.position.set(0, -len / 2 - rad, 0);
    g.add(m);
    seg[key] = m; m.userData.group = g;
    return g;
  }

  // 중심이 그룹 원점에 오는 박스 세그먼트(그룹 반환)
  function box(parent, key, x, y, z, w, h, d, cy) {
    var g = new THREE.Group();
    g.position.set(x, y, z);
    parent.add(g);
    var m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(COL_BASE));
    m.position.set(0, cy == null ? 0 : cy, 0);
    g.add(m);
    seg[key] = m; m.userData.group = g;
    return g;
  }

  function buildMannequin() {
    mannequin = new THREE.Group();
    rootPivot = new THREE.Group();       // 전체 자세 회전/위치용
    rootPivot.position.set(0, 0.02, 0);
    mannequin.add(rootPivot);

    // 골반(hips y=0.95) → 아래몸통 → 위몸통 → 목 → 머리
    var pelvisG = box(rootPivot, "pelvis", 0, 0.95, 0, 0.30, 0.20, 0.20, 0);
    var tlG = box(pelvisG, "torsoLower", 0, 0.10, 0, 0.30, 0.26, 0.19, 0.13);
    var tuG = box(tlG, "torsoUpper", 0, 0.26, 0, 0.36, 0.32, 0.20, 0.16);
    var neckG = new THREE.Group(); neckG.position.set(0, 0.32, 0); tuG.add(neckG);
    var neckM = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.09, 6, 12), mat(COL_BASE));
    neckM.position.set(0, 0.07, 0); neckG.add(neckM); seg.neck = neckM; neckM.userData.group = neckG;
    var headG = new THREE.Group(); headG.position.set(0, 0.14, 0); neckG.add(headG);
    var headM = new THREE.Mesh(new THREE.SphereGeometry(0.12, 20, 16), mat(COL_BASE));
    headM.position.set(0, 0.12, 0); headG.add(headM); seg.head = headM; headM.userData.group = headG;

    // 팔: 어깨(위몸통 상단 좌우), 메시는 아래로 뻗음
    var shTopY = 0.30, shX = 0.24;
    var uAL = limb(tuG, "upperArmL", shX, shTopY, 0, 0.28, 0.055);
    var uAR = limb(tuG, "upperArmR", -shX, shTopY, 0, 0.28, 0.055);
    var fAL = limb(uAL, "foreArmL", 0, -0.28 - 0.11, 0, 0.24, 0.05);
    var fAR = limb(uAR, "foreArmR", 0, -0.28 - 0.11, 0, 0.24, 0.05);
    limb(fAL, "handL", 0, -0.24 - 0.10, 0, 0.09, 0.045);
    limb(fAR, "handR", 0, -0.24 - 0.10, 0, 0.09, 0.045);

    // 다리: 골반 하단 좌우
    var hipX = 0.10, hipY = -0.12;
    var thL = limb(pelvisG, "thighL", hipX, hipY, 0, 0.42, 0.075);
    var thR = limb(pelvisG, "thighR", -hipX, hipY, 0, 0.42, 0.075);
    var shL = limb(thL, "shinL", 0, -0.42 - 0.15, 0, 0.42, 0.06);
    var shR = limb(thR, "shinR", 0, -0.42 - 0.15, 0, 0.42, 0.06);
    // 발: 앞(+Z)으로 뻗게
    var ftL = new THREE.Group(); ftL.position.set(0, -0.42 - 0.12, 0); shL.add(ftL);
    var ftR = new THREE.Group(); ftR.position.set(0, -0.42 - 0.12, 0); shR.add(ftR);
    var footGeo = new THREE.BoxGeometry(0.09, 0.06, 0.20);
    var fmL = new THREE.Mesh(footGeo, mat(COL_BASE)); fmL.position.set(0, -0.02, 0.07); ftL.add(fmL); seg.footL = fmL; fmL.userData.group = ftL;
    var fmR = new THREE.Mesh(footGeo.clone(), mat(COL_BASE)); fmR.position.set(0, -0.02, 0.07); ftR.add(fmR); seg.footR = fmR; fmR.userData.group = ftR;

    scene.add(mannequin);
  }

  function makeLabelSprite(text) {
    var cv = document.createElement("canvas");
    var pad = 16, fs = 34;
    var ctx = cv.getContext("2d");
    ctx.font = "bold " + fs + "px sans-serif";
    var w = ctx.measureText(text).width;
    cv.width = w + pad * 2; cv.height = fs + pad * 2;
    ctx = cv.getContext("2d");
    ctx.font = "bold " + fs + "px sans-serif";
    ctx.fillStyle = "rgba(20,22,28,0.86)";
    roundRect(ctx, 0, 0, cv.width, cv.height, 12); ctx.fill();
    ctx.fillStyle = "#ff8a5a"; ctx.textBaseline = "middle";
    ctx.fillText(text, pad, cv.height / 2);
    var tex = new THREE.CanvasTexture(cv); tex.needsUpdate = true;
    var spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
    spr.renderOrder = 10;   // 근육 강조(renderOrder 3)보다 위에 떠야 글씨가 안 묻힌다
    var sc = 0.0011;        // 화면 대비 라벨이 너무 커서 겹치던 문제로 축소
    spr.scale.set(cv.width * sc, cv.height * sc, 1);
    return spr;
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath(); ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
  }

  // 실제 근육 3D 메시(Z-Anatomy 유래, app/assets/muscles.glb) — 앱 생명주기 동안 1회만 로드해 재사용.
  // 마네킹은 리깅이 없는 절차적 지오메트리라 근육 메시와 뼈대 연결이 안 됨 — "서기" 자세일 때만 오버레이 표시.
  var muscleAssets = { group: null, mapping: null, ready: false, promise: null };
  var MANNEQUIN_STANDING_HEIGHT = 2.36; // buildMannequin() 고정 치수 실측(발바닥 -0.31 ~ 머리끝 2.05, "서기")
  var MANNEQUIN_STANDING_FOOT_Y = -0.31;
  var ROOT_PIVOT_Y = 0.02;              // rootPivot.position.y — 근육 그룹이 이 노드의 자식이라 보정 필요
  // Z-Anatomy 원본은 "바닥 y=0"인 실제 사람 치수(미터)다. 실측으로 확인한 랜드마크:
  //   정강이근 0.04~0.41 / 대둔근 0.71~0.98 / 대흉근 1.17~1.41 / 어깨올림근 1.39~1.54
  // 대둔근 상단(엉덩뼈 능선) 0.98m 기준으로 역산한 원본 모델의 키. 근육 데이터는 목에서 끝나므로
  // "메시 전체 높이"를 마네킹 키에 맞추면 안 된다(예전 버그: 목 근육이 머리 위로 떠올랐음).
  var ZANATOMY_STATURE = 1.75;
  var COL_FLESH = 0x9c4038, EMIS_FLESH = 0x2a0d0a;

  function loadMuscleAssets() {
    if (muscleAssets.promise) return muscleAssets.promise;
    var loader = new GLTFLoader();
    muscleAssets.promise = Promise.all([
      new Promise(function (resolve, reject) {
        loader.load("assets/muscles.glb", function (gltf) { resolve(gltf.scene); }, undefined, reject);
      }),
      fetch("assets/muscle_object_mapping.json").then(function (r) { return r.json(); })
    ]).then(function (res) {
      var group = res[0];
      muscleAssets.mapping = res[1];
      // 실제 키 기준 스케일 + 바닥(y=0)을 마네킹 발바닥에 정렬. rootPivot 자식으로 붙으므로 그만큼 뺀다.
      group.scale.setScalar(MANNEQUIN_STANDING_HEIGHT / ZANATOMY_STATURE);
      group.position.set(0, MANNEQUIN_STANDING_FOOT_Y - ROOT_PIVOT_Y, 0);
      // 기본 상태: 전신 근육을 살색으로 은은하게 다 보여준다(= 몸이 근육으로 보이게).
      // 선택된 근육만 applyMuscleOverlay가 주황으로 끌어올린다.
      group.traverse(function (o) {
        if (o.isMesh) {
          o.material = o.material.clone();
          o.visible = true;
          dressMuscle(o, false);
        }
      });
      muscleAssets.group = group;
      muscleAssets.ready = true;
      return group;
    }).catch(function (err) {
      muscleAssets.ready = false;
      if (window.console) console.warn("[RTSViz] 실제 근육 메시 로드 실패(부위 강조 방식으로 계속 동작):", err);
    });
    return muscleAssets.promise;
  }

  // 근육 메시 1개의 표시 상태를 정한다. target=true면 시술 대상(주황 강조), false면 배경 근육(살색 반투명).
  // 배경을 반투명 + depthWrite:false로 두면 몸 속 깊은 근육(예: 견갑하근)도 비쳐 보인다.
  function dressMuscle(mesh, target) {
    var m = mesh.material;
    if (target) {
      // ★ 불투명(transparent:false)으로 두면 three.js가 이걸 먼저 그리고 그 위에 반투명 배경
      //   근육을 덮어버려서 색이 죽는다. 특히 견갑하근처럼 몸 안쪽 근육은 거의 안 보인다.
      //   transparent + 높은 renderOrder + depthTest:false 로 항상 맨 위에 그리게 한다.
      m.color.setHex(COL_TARGET); m.emissive.setHex(EMIS_TARGET); m.emissiveIntensity = 0.5;
      m.transparent = true; m.opacity = 1; m.depthWrite = false; m.depthTest = false;
      mesh.renderOrder = 3;
    } else {
      m.color.setHex(COL_FLESH); m.emissive.setHex(EMIS_FLESH); m.emissiveIntensity = 0.12;
      m.transparent = true; m.opacity = 0.32; m.depthWrite = false; m.depthTest = true;
      mesh.renderOrder = 1;
    }
    m.needsUpdate = true;
  }

  // 선택된 근육을 주황으로 강조하고 나머지는 살색 배경으로 되돌린다.
  // 반환값: 강조된 근육의 월드 중심(카메라가 그 부위를 바라보게 하는 데 씀). 없으면 null.
  function applyMuscleOverlay(zAnatomy, poseTag) {
    if (!muscleAssets.ready || !muscleAssets.group) return null;
    // 근육 그룹이 rootPivot의 자식이라 마네킹 전신 회전(자세 전환)은 함께 따라감.
    // 단, 관절별 리깅은 없어 팔다리 세부 각도까지는 못 따라감(전신 방향만 근사).
    var ids = (zAnatomy && muscleAssets.mapping && muscleAssets.mapping[zAnatomy]) || [];
    // glTF export 시 material 슬롯이 여러 개인 오브젝트는 프리미티브별로 자식 노드가 나뉘어
    // "muscle_0042", "muscle_0042_1" 처럼 접미사가 붙을 수 있어 접두어 일치로 매칭한다.
    function matches(name) {
      for (var i = 0; i < ids.length; i++) {
        var id = ids[i];
        if (name === id || name.indexOf(id + "_") === 0 || name.indexOf(id + ".") === 0) return true;
      }
      return false;
    }
    var hit = new THREE.Box3(), found = false;
    muscleAssets.group.updateMatrixWorld(true);
    muscleAssets.group.traverse(function (o) {
      if (!o.isMesh) return;
      var isTarget = matches(o.name);
      dressMuscle(o, isTarget);
      if (isTarget) {
        var bb = new THREE.Box3().setFromObject(o);
        if (!found) { hit.copy(bb); found = true; } else hit.union(bb);
      }
    });
    if (!found) return null;
    var c = new THREE.Vector3(); hit.getCenter(c);
    return c;
  }

  function clearOverlays() {
    [handSprite, arrowHelper, labelSprite].forEach(function (o) { if (o) scene.remove(o); });
    handSprite = arrowHelper = labelSprite = null;
  }

  // 실제 근육이 있으면 그 부위를 덮는 마네킹 상자·막대는 아예 감춘다.
  // (안 감추면 몸통 상자가 근육 뒤에 "의자"처럼 비쳐서 지저분하다.)
  // 근육 데이터에 없는 부위(머리·손·발)만 방향을 알아볼 정도로 옅게 남긴다.
  var MUSCLE_COVERED = ["pelvis", "torsoLower", "torsoUpper", "neck",
                        "upperArmL", "upperArmR", "foreArmL", "foreArmR",
                        "thighL", "thighR", "shinL", "shinR"];

  function resetColors() {
    var hasMuscle = muscleAssets.ready;
    Object.keys(seg).forEach(function (k) {
      var mesh = seg[k], m = mesh.material;
      var covered = hasMuscle && MUSCLE_COVERED.indexOf(k) >= 0;
      mesh.visible = !covered;
      m.color.setHex(COL_DIM); m.transparent = true;
      m.opacity = hasMuscle ? 0.16 : 0.30;
      m.emissive.setHex(0x000000); m.emissiveIntensity = 0;
      m.depthWrite = !hasMuscle;
      m.needsUpdate = true;
    });
  }

  function expandKeys(keys) {
    var out = [];
    (keys || []).forEach(function (k) {
      if (BILATERAL[k]) out = out.concat(BILATERAL[k]); else out.push(k);
    });
    return out;
  }

  function worldCenter(mesh) {
    var v = new THREE.Vector3();
    mesh.getWorldPosition(v); return v;
  }

  function setHighlight(meshKeys, face, label, zAnatomy) {
    if (!mounted) return;
    resetColors();
    clearOverlays();
    lastZAnatomy = zAnatomy || "";
    var muscleCenter = applyMuscleOverlay(lastZAnatomy, currentPoseTag);
    var hasMuscle = !!muscleCenter;
    var keys = expandKeys(meshKeys).filter(function (k) { return seg[k]; });
    var center = new THREE.Vector3(), n = 0;
    keys.forEach(function (k) {
      var m = seg[k].material;
      // 실제 근육 형상이 있으면 마네킹은 부위를 옅게 비춰주기만 한다(주황 상자로 덮지 않는다).
      if (hasMuscle) {
        m.color.setHex(COL_TARGET); m.transparent = true; m.opacity = 0.14;
        m.emissive.setHex(EMIS_TARGET); m.emissiveIntensity = 0.10; m.depthWrite = false;
      } else {
        m.color.setHex(COL_TARGET); m.transparent = false; m.opacity = 1;
        m.emissive.setHex(EMIS_TARGET); m.emissiveIntensity = 0.55; m.depthWrite = true;
      }
      m.needsUpdate = true;
      center.add(worldCenter(seg[k])); n++;
    });
    if (!n && !hasMuscle) return;
    // 실제 근육이 있으면 그 근육의 실제 위치를 기준으로 삼는다(마네킹 부위 중심보다 정확).
    if (hasMuscle) center.copy(muscleCenter);
    else center.multiplyScalar(1 / n);

    // 방향 화살표(face 기준 대략): front=+Z, back=-Z, side=+X, inner=-X
    var dir = new THREE.Vector3(0, 0, 1);
    if (face === "back") dir.set(0, 0, -1);
    else if (face === "side") dir.set(1, 0, 0);
    else if (face === "inner") dir.set(-1, 0, 0);
    var origin = center.clone().addScaledVector(dir, 0.55);
    arrowHelper = new THREE.ArrowHelper(dir.clone().negate(), origin, 0.42, 0xff7a3c, 0.12, 0.08);
    scene.add(arrowHelper);

    // 시술자 손 표시 — 근육 라벨과 화면에서 겹치지 않게 화살표 쪽 아래로 내린다.
    handSprite = makeLabelSprite("✋ 시술 방향");
    handSprite.position.copy(origin).add(new THREE.Vector3(0, -0.16, 0));
    scene.add(handSprite);

    // 근육 라벨 — 대상 부위 위쪽에 띄운다.
    if (label) {
      labelSprite = makeLabelSprite(label);
      labelSprite.position.copy(center).add(new THREE.Vector3(0, 0.34, 0));
      scene.add(labelSprite);
    }
    // 카메라를 대상 부위로 이동시키고, 그 근육이 있는 면(앞/뒤/옆)을 바라보게 돌린다.
    // (등 근육인데 앞에서 보고 있으면 강조가 몸에 가려 안 보인다.)
    camTarget.copy(center);
    if (face === "back") yaw = Math.PI;
    else if (face === "side") yaw = Math.PI / 2;
    else if (face === "inner") yaw = -Math.PI / 2;
    else yaw = 0;
    yaw += 0.35;   // 정면 정중앙보다 살짝 비스듬해야 입체감이 산다
    pitch = 0.08;
    dist = 2.5;    // 대상 부위 주변 몸까지 같이 보여야 어디인지 파악된다
    requestRender();
  }

  var camTarget = new THREE.Vector3(0, 0.95, 0);

  function setPose(tag) {
    if (!mounted) return;
    var p = POSES[tag] || POSES["서기"];
    // 모든 관절 초기화
    ["neck", "torsoLower", "torsoUpper", "upperArmL", "upperArmR", "foreArmL", "foreArmR",
     "thighL", "thighR", "shinL", "shinR", "footL", "footR", "head"].forEach(function (k) {
      if (seg[k] && seg[k].userData.group) seg[k].userData.group.rotation.set(0, 0, 0);
    });
    var r = p.root || { pos: [0, 0, 0], rot: [0, 0, 0] };
    rootPivot.position.set(r.pos[0], 0.02 + r.pos[1], r.pos[2]);
    rootPivot.rotation.set(r.rot[0], r.rot[1], r.rot[2]);
    Object.keys(p).forEach(function (k) {
      if (k === "root") return;
      if (seg[k] && seg[k].userData.group) seg[k].userData.group.rotation.set(p[k][0], p[k][1], p[k][2]);
    });
    currentPoseTag = POSES[tag] ? tag : "서기";
    applyMuscleOverlay(lastZAnatomy, currentPoseTag);
    requestRender();
    return currentPoseTag;
  }

  function onResize() {
    if (!renderer) return;
    var w = canvas.clientWidth, h = canvas.clientHeight;
    if (w === 0 || h === 0) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
    requestRender();
  }

  // 온디맨드 렌더링(연속 rAF 대신) — 변화가 있을 때만 1프레임 그림.
  // → 페이지가 idle 상태가 되어 스크린샷/저전력에 유리.
  function renderFrame() {
    raf = null;
    if (!renderer) return;
    var cx = Math.cos(pitch) * Math.sin(yaw) * dist;
    var cy = camTarget.y + Math.sin(pitch) * dist;
    var cz = Math.cos(pitch) * Math.cos(yaw) * dist;
    camera.position.set(cx, cy, cz);
    camera.lookAt(camTarget);
    renderer.render(scene, camera);
  }
  function requestRender() {
    if (!mounted || raf) return;
    raf = requestAnimationFrame(renderFrame);
  }

  function bindDrag() {
    function down(e) { dragging = true; var p = pt(e); lastX = p.x; lastY = p.y; }
    function move(e) {
      if (!dragging) return;
      var p = pt(e);
      yaw -= (p.x - lastX) * 0.01; pitch += (p.y - lastY) * 0.01;
      pitch = Math.max(-1.3, Math.min(1.3, pitch));
      lastX = p.x; lastY = p.y;
      requestRender();
      if (e.cancelable) e.preventDefault();
    }
    function up() { dragging = false; }
    function pt(e) { var t = e.touches ? e.touches[0] : e; return { x: t.clientX, y: t.clientY }; }
    canvas.addEventListener("mousedown", down); window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
    canvas.addEventListener("touchstart", down, { passive: true }); canvas.addEventListener("touchmove", move, { passive: false }); canvas.addEventListener("touchend", up);
    canvas.addEventListener("wheel", function (e) { dist = Math.max(1.6, Math.min(6, dist + (e.deltaY > 0 ? 0.3 : -0.3))); requestRender(); e.preventDefault(); }, { passive: false });
  }

  function mount(canvasEl) {
    canvas = canvasEl;
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1116);
    camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    var hemi = new THREE.HemisphereLight(0xffffff, 0x33383f, 0.9); scene.add(hemi);
    var dir = new THREE.DirectionalLight(0xffffff, 0.8); dir.position.set(2, 4, 3); scene.add(dir);
    var dir2 = new THREE.DirectionalLight(0x88aaff, 0.35); dir2.position.set(-3, 1, -2); scene.add(dir2);
    // 바닥 그리드
    var grid = new THREE.GridHelper(4, 12, 0x2a3038, 0x1c2128); grid.position.y = 0; scene.add(grid);
    seg = {};
    buildMannequin();
    mounted = true;
    bindDrag();
    onResize();
    window.addEventListener("resize", onResize);
    resetColors();
    requestRender();
    // 초기 리사이즈 보정(레이아웃 후)
    setTimeout(onResize, 60); setTimeout(onResize, 250); setTimeout(onResize, 600);

    // 실제 근육 메시(있으면) 씬에 추가 — 최초 1회 로드 후 캐시 재사용, 로드 전 unmount됐으면 무시
    loadMuscleAssets().then(function (group) {
      // rootPivot의 자식으로 붙여 자세 전환(전신 회전/이동)을 마네킹과 함께 따라가게 함
      if (group && mounted && rootPivot) {
        rootPivot.add(group);
        // 근육이 준비되면 마네킹을 실루엣 수준으로 낮춰야 하므로 색을 다시 깔고 강조를 재적용한다.
        resetColors();
        var c = applyMuscleOverlay(lastZAnatomy, currentPoseTag);
        if (c) camTarget.copy(c);
        requestRender();
      }
    });
  }

  function unmount() {
    if (raf) cancelAnimationFrame(raf);
    raf = null; mounted = false;
    window.removeEventListener("resize", onResize);
    if (renderer) { renderer.dispose && renderer.dispose(); }
    scene = camera = renderer = null; seg = {};
  }

  function debugColors() {
    var o = {};
    Object.keys(seg).forEach(function (k) {
      var m = seg[k].material;
      o[k] = m.color.getHexString() + "@" + (+m.opacity).toFixed(2);
    });
    return o;
  }

  function debugBounds() {
    if (!mannequin) return null;
    var box = new THREE.Box3().setFromObject(mannequin);
    var size = new THREE.Vector3(); box.getSize(size);
    return { min: box.min.toArray(), max: box.max.toArray(), size: size.toArray() };
  }

  // 진단용. 강조 근육(주황)과 배경 근육(살색)을 나눠서 보고한다.
  // ※ 반드시 월드 행렬을 먼저 갱신한다 — 안 그러면 직전 자세의 좌표를 읽어 엉뚱한 값이 나온다.
  function debugMuscleOverlay() {
    if (!muscleAssets.group) return { ready: muscleAssets.ready, targetCount: 0 };
    muscleAssets.group.updateMatrixWorld(true);
    var target = [], tBox = new THREE.Box3(), tFirst = true;
    var allBox = new THREE.Box3(), aFirst = true, allCount = 0;
    muscleAssets.group.traverse(function (o) {
      if (!o.isMesh) return;
      var bb = new THREE.Box3().setFromObject(o);
      allCount++;
      if (aFirst) { allBox.copy(bb); aFirst = false; } else allBox.union(bb);
      if (o.renderOrder === 3) {  // dressMuscle(target=true)가 매기는 값
        target.push(o.name);
        if (tFirst) { tBox.copy(bb); tFirst = false; } else tBox.union(bb);
      }
    });
    function fmt(b, ok) { return ok ? { min: b.min.toArray().map(function (n) { return +n.toFixed(3); }),
                                        max: b.max.toArray().map(function (n) { return +n.toFixed(3); }) } : null; }
    return {
      ready: muscleAssets.ready,
      meshCount: allCount,
      targetCount: target.length,
      targetNames: target,
      targetBounds: fmt(tBox, !tFirst),
      bodyBounds: fmt(allBox, !aFirst),
      groupScale: muscleAssets.group.scale.x,
      groupPos: muscleAssets.group.position.toArray()
    };
  }

  // 진단용: requestAnimationFrame을 기다리지 않고 즉시 1프레임 그린다.
  // (백그라운드 탭에서는 rAF가 거의 안 돌아 화면 캡처 검증이 불가능하므로 필요)
  function debugRenderNow() {
    if (!renderer) return false;
    if (raf) { cancelAnimationFrame(raf); raf = null; }
    renderFrame();
    return true;
  }

  return { mount: mount, unmount: unmount, setPose: setPose, setHighlight: setHighlight,
           poses: Object.keys(POSES), debugColors: debugColors, debugBounds: debugBounds,
           debugMuscleOverlay: debugMuscleOverlay, debugRenderNow: debugRenderNow };
})();
